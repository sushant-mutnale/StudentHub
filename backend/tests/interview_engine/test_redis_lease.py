import json

import pytest

from backend.interview_engine.adapters.memory_store import InMemorySessionStore
from backend.interview_engine.adapters.redis_lease import RedisLease
from backend.interview_engine.adapters.system import InMemoryLease


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.expiries = {}
        self.set_reply = True

    async def set(self, key, value, nx=False, ex=None):
        if nx and key in self.values:
            return False
        self.values[key] = value
        self.expiries[key] = ex
        return self.set_reply

    async def get(self, key):
        return self.values.get(key)

    async def eval(self, script, numkeys, *args):
        key, token = args[0], args[1]
        raw = self.values.get(key)
        if raw is None:
            return 0
        if json.loads(raw).get("token") == token:
            self.values.pop(key, None)
            return 1
        return 0


@pytest.mark.asyncio
async def test_redis_lease_acquire_confirm_takeover():
    lease = RedisLease(FakeRedis())
    assert await lease.acquire("s1", "d1", "t1", 60) is True
    assert await lease.acquire("s1", "d2", "t2", 60) is False
    assert await lease.confirm("s1", "d1", "t1") is True
    assert await lease.confirm("s1", "d2", "t2") is False
    assert await lease.takeover("s1", "d2", "t2", 60) is True
    assert await lease.confirm("s1", "d2", "t2") is True
    await lease.release("s1", "t2")
    assert await lease.acquire("s1", "d3", "t3", 60) is True


@pytest.mark.asyncio
async def test_release_ignores_a_stale_token():
    redis = FakeRedis()
    lease = RedisLease(redis)
    assert await lease.acquire("s1", "d1", "t1", 60) is True
    await lease.release("s1", "stale")
    assert await lease.confirm("s1", "d1", "t1") is True
    await lease.release("s1", "t1")
    assert await lease.confirm("s1", "d1", "t1") is False
    assert await lease.acquire("s1", "d2", "t2", 60) is True


@pytest.mark.asyncio
async def test_release_script_is_token_guarded_in_real_redis():
    import os

    import redis.asyncio as aioredis

    port = int(os.environ.get("REDIS_PORT", "6379"))
    client = aioredis.Redis(host="localhost", port=port, decode_responses=True)
    try:
        await client.ping()
    except Exception:
        pytest.skip(f"no Redis reachable on localhost:{port}")

    key = "interview_engine:lease:fix1-probe"
    try:
        await client.delete(key)
        lease = RedisLease(client)
        assert await lease.acquire("fix1-probe", "d1", "t1", 60) is True

        await lease.release("fix1-probe", "stale")
        assert await client.get(key) is not None
        assert await lease.confirm("fix1-probe", "d1", "t1") is True

        await lease.release("fix1-probe", "t1")
        assert await client.get(key) is None
    finally:
        await client.delete(key)
        await client.aclose()


@pytest.mark.asyncio
async def test_lease_ttl_and_per_session_keys():
    redis = FakeRedis()
    lease = RedisLease(redis)
    assert await lease.acquire("s1", "d1", "t1", 45) is True
    assert await lease.acquire("s2", "d2", "t2", 60) is True
    assert redis.expiries["interview_engine:lease:s1"] == 45
    assert redis.expiries["interview_engine:lease:s2"] == 60
    assert await lease.confirm("s1", "d2", "t2") is False
    assert await lease.confirm("s2", "d2", "t2") is True


@pytest.mark.asyncio
async def test_acquire_and_takeover_return_strict_bools_for_a_raw_ok_reply():
    redis = FakeRedis()
    redis.set_reply = "OK"
    lease = RedisLease(redis)
    assert await lease.acquire("s1", "d1", "t1", 60) is True
    assert await lease.takeover("s1", "d2", "t2", 60) is True


@pytest.mark.asyncio
async def test_confirm_returns_false_for_a_corrupt_value():
    redis = FakeRedis()
    lease = RedisLease(redis)
    redis.values["interview_engine:lease:s1"] = "{not json"
    assert await lease.confirm("s1", "d1", "t1") is False


@pytest.mark.asyncio
async def test_confirm_rejects_a_byte_value_that_parses_only_without_decoding():
    redis = FakeRedis()
    lease = RedisLease(redis)
    redis.values["interview_engine:lease:s1"] = json.dumps(
        {"device_id": "d1", "token": "t1"}
    ).encode("utf-8-sig")
    assert await lease.confirm("s1", "d1", "t1") is False


@pytest.mark.asyncio
async def test_confirm_returns_false_for_a_non_object_json_value():
    redis = FakeRedis()
    lease = RedisLease(redis)
    redis.values["interview_engine:lease:s1"] = "[1, 2]"
    assert await lease.confirm("s1", "d1", "t1") is False


def test_factory_wires_the_injected_ports():
    from backend.interview_engine.adapters.factory import build_engine
    from backend.interview_engine.adapters.scripted import (
        DeterministicEvaluator,
        HeuristicAnalyzer,
        ScriptedQuestionGenerator,
    )
    from backend.interview_engine.application.engine import InterviewEngine

    store = InMemorySessionStore()
    lease = InMemoryLease()
    engine = build_engine(store=store, lease=lease)
    assert isinstance(engine, InterviewEngine)
    assert engine.store is store
    assert engine.lease is lease
    assert isinstance(engine.analyzer, HeuristicAnalyzer)
    assert isinstance(engine.generator, ScriptedQuestionGenerator)
    assert isinstance(engine.evaluator, DeterministicEvaluator)
    assert engine.clock.__class__.__name__ == "SystemClock"
    assert engine.ids.__class__.__name__ == "UuidIds"


def test_factory_defaults_to_an_in_memory_lease_without_redis():
    from backend.interview_engine.adapters.factory import build_engine

    engine = build_engine(store=InMemorySessionStore())
    assert isinstance(engine.lease, InMemoryLease)
