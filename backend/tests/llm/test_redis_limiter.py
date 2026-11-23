import uuid

import pytest

from backend.services.llm.limiter import Budgets, InMemoryRateLimiter
from backend.services.llm.redis_limiter import FallbackRateLimiter, RedisRateLimiter


class FakeClock:
    def __init__(self, now_ms: int = 1_000_000):
        self.now_ms = now_ms

    def __call__(self) -> int:
        return self.now_ms


async def _real_limiter(client, rpm=10, rpd=100, tpm=1000, tpd=10000):
    clock = FakeClock()
    limiter = RedisRateLimiter(
        client,
        Budgets(rpm=rpm, rpd=rpd, tpm=tpm, tpd=tpd),
        clock=clock,
    )
    return limiter, clock


async def test_redis_limiter_enforces_tokens_and_refunds_on_settle():
    import os

    import redis.asyncio as aioredis

    port = int(os.environ.get("REDIS_PORT", "6379"))
    client = aioredis.Redis(host="localhost", port=port, decode_responses=True)
    try:
        await client.ping()
    except Exception:
        pytest.skip(f"no Redis reachable on localhost:{port}")

    keyhash = f"test-{uuid.uuid4().hex[:12]}"
    prefix = f"llm:rl:{keyhash}:"
    try:
        limiter, _ = await _real_limiter(client, tpm=250)
        first = await limiter.reserve(keyhash, 200)
        assert first.reservation is not None

        denied = await limiter.reserve(keyhash, 100)
        assert denied.reservation is None
        assert denied.reason == "minute_tokens"

        await limiter.settle(first.reservation, actual_tokens=50)
        again = await limiter.reserve(keyhash, 200)
        assert again.reservation is not None
    finally:
        keys = [f"{prefix}{name}" for name in ("min", "tokens", "tokamt", "day", "daytok", "block")]
        await client.delete(*keys)
        await client.aclose()


async def test_redis_limiter_block_round_trips():
    import os

    import redis.asyncio as aioredis

    port = int(os.environ.get("REDIS_PORT", "6379"))
    client = aioredis.Redis(host="localhost", port=port, decode_responses=True)
    try:
        await client.ping()
    except Exception:
        pytest.skip(f"no Redis reachable on localhost:{port}")

    keyhash = f"test-{uuid.uuid4().hex[:12]}"
    try:
        limiter, _ = await _real_limiter(client)
        await limiter.block(keyhash, seconds=30)
        denied = await limiter.reserve(keyhash, 1)
        assert denied.reservation is None
        assert denied.reason == "blocked"
        assert 0 < denied.wait_ms <= 30_000
    finally:
        await client.delete(f"llm:rl:{keyhash}:block")
        await client.aclose()


async def test_fallback_limiter_uses_memory_when_redis_raises():
    class BrokenRedis:
        async def eval(self, *args, **kwargs):
            raise ConnectionError("redis is down")

        async def set(self, *args, **kwargs):
            raise ConnectionError("redis is down")

    budgets = Budgets(rpm=1, rpd=10, tpm=100, tpd=1000)
    limiter = FallbackRateLimiter(
        RedisRateLimiter(BrokenRedis(), budgets),
        InMemoryRateLimiter(budgets),
    )
    first = await limiter.reserve("kh", 10)
    assert first.reservation is not None
    second = await limiter.reserve("kh", 10)
    assert second.reservation is None
    assert second.reason == "minute_requests"


async def test_fallback_limiter_logs_degradation_only_once():
    class BrokenRedis:
        async def eval(self, *args, **kwargs):
            raise ConnectionError("redis is down")

    records = []

    class RecordingLogger:
        def warning(self, message, *args, **kwargs):
            records.append(message)

        def info(self, message, *args, **kwargs):
            records.append(message)

    budgets = Budgets(rpm=10, rpd=10, tpm=100, tpd=1000)
    limiter = FallbackRateLimiter(
        RedisRateLimiter(BrokenRedis(), budgets),
        InMemoryRateLimiter(budgets),
        logger=RecordingLogger(),
    )
    await limiter.reserve("kh", 1)
    await limiter.reserve("kh", 1)
    await limiter.reserve("kh", 1)
    assert len(records) == 1
