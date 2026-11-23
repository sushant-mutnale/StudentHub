# Groq LLM Wrapper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the interview engine real `Analyzer`/`QuestionGenerator`/`Evaluator` adapters backed by Groq `openai/gpt-oss-120b`, protected by a shared Redis rate limiter with 3-key rotation, so a real interview runs end to end without any provider outage or rate limit blocking a candidate.

**Architecture:** A provider-agnostic infrastructure package `backend/services/llm/` (key pool, rate limiter, Groq client, prompts) sits below a thin policy layer `backend/interview_engine/adapters/llm.py` that implements the engine's existing ports and owns every fallback decision. The engine itself gains one guard so a raising analyzer cannot 500 a candidate's answer. Real adapters activate only when `groq_llm_enabled` is true; scripted adapters stay the default.

**Tech Stack:** Python 3.12, `openai` 2.17.0 (`AsyncOpenAI` against Groq's OpenAI-compatible endpoint), `redis.asyncio` 7.1.0 with Lua scripts, pydantic-settings 2.x, pytest with `asyncio_mode = auto`.

**Spec:** `docs/superpowers/specs/2026-11-23-groq-llm-wrapper-design.md`

## Global Constraints

- Provider limits per key: 30 RPM, 1,000 RPD, 8,000 TPM, 200,000 TPD. Internal budgets default to 25 / 900 / 7,000 / 180,000.
- Model id `openai/gpt-oss-120b`; `max_completion_tokens`, never the deprecated `max_tokens`.
- `reasoning_effort` accepts only `low`, `medium`, `high` for this model; default `low`.
- Reasoning tokens count against both the completion cap and the token budget. `finish_reason == "length"` means the response is unusable.
- Windows are rolling: 60 seconds exactly for minute limits, trailing 25 hourly buckets for daily limits (over-count, never under-count).
- No HTTP call may hang; every wait is `asyncio.sleep` bounded by `groq_max_wait_seconds`.
- API keys live only in `backend/.env` (gitignored). Raw keys never enter Redis, logs, exceptions, or `repr()`. Only `sha256(key)[:16]` fingerprints do.
- Adapters never leak transport errors: analyzer and generator return the engine's degraded value; evaluator raises the typed `LLMUnavailable` that the report path already handles.
- `groq_llm_enabled` defaults to `false`. The default test suite must pass with no API key and no Redis.
- No comments in production code. No `git add -A` or `git add .`; stage explicit paths only.
- Run tests from the worktree root with `$env:REDIS_PORT='6380'` set first (6379 is occupied by `corunner-redis`). Windows PowerShell: chain with `;`, never `&&`.

## File Map

Create:

- `backend/services/llm/__init__.py` — re-exports the public surface.
- `backend/services/llm/limiter.py` — `Budgets`, `Reservation`, `ReserveResult`, `RateLimiter` protocol, `InMemoryRateLimiter`.
- `backend/services/llm/redis_limiter.py` — `RedisRateLimiter` (Lua), `FallbackRateLimiter`.
- `backend/services/llm/keys.py` — `ApiKey`, `fingerprint`, `ApiKeyPool`.
- `backend/services/llm/groq.py` — `LLMUnavailable`, `LLMCompletion`, `estimate_tokens`, `GroqLLMClient`.
- `backend/services/llm/prompts.py` — system prompts and user-message builders.
- `backend/interview_engine/adapters/llm.py` — `GroqAnalyzer`, `GroqQuestionGenerator`, `GroqEvaluator`, `LLMAdapters`, `build_llm_adapters`.
- `backend/tests/llm/__init__.py`
- `backend/tests/llm/test_in_memory_limiter.py`
- `backend/tests/llm/test_redis_limiter.py`
- `backend/tests/llm/test_keys.py`
- `backend/tests/llm/test_groq_client.py`
- `backend/tests/llm/test_adapters.py`
- `backend/tests/llm/test_live_interview.py`

Modify:

- `backend/config.py` — Groq settings block.
- `backend/interview_engine/application/engine.py` — analyzer guard.
- `backend/interview_engine/adapters/factory.py` — opt-in LLM adapters.
- `pytest.ini` — `llm` marker.
- `backend/tests/interview_engine/test_engine_submit.py` or a new file — the guard test (new file `test_engine_analyzer_guard.py` is cleaner).

Dependency direction, enforced by review: `services/llm/*` imports nothing from `interview_engine`; `adapters/llm.py` never constructs an HTTP client; nothing outside `adapters/llm.py` reads `groq_llm_enabled`.

---

### Task 1: Config, limiter contracts, and the in-memory limiter

**Files:**
- Modify: `backend/config.py` (insert after the Rate Limiting block, around line 84)
- Create: `backend/services/llm/__init__.py`
- Create: `backend/services/llm/limiter.py`
- Create: `backend/tests/llm/__init__.py`
- Create: `backend/tests/llm/test_in_memory_limiter.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `Budgets(rpm: int, rpd: int, tpm: int, tpd: int)` frozen dataclass.
  - `Reservation(keyhash: str, request_id: str, tokens: int, at_ms: int)` frozen dataclass.
  - `ReserveResult(reservation: Optional[Reservation], wait_ms: int, reason: str)` frozen dataclass.
  - `RateLimiter` protocol with `async reserve(keyhash: str, tokens: int) -> ReserveResult`, `async settle(reservation: Reservation, actual_tokens: int) -> None`, `async block(keyhash: str, seconds: float) -> None`.
  - `InMemoryRateLimiter(budgets: Budgets, clock: Callable[[], int] | None = None)`.
  - Settings fields `groq_api_key_1..3`, `groq_model`, `groq_base_url`, `groq_rpm_per_key`, `groq_rpd_per_key`, `groq_tpm_per_key`, `groq_tpd_per_key`, `groq_max_wait_seconds`, `groq_request_timeout_seconds`, `groq_reasoning_effort`, `groq_llm_enabled`.

- [ ] **Step 1: Add the Groq settings block**

Insert into `Settings` in `backend/config.py` directly after the Rate Limiting block (after `rate_limit_auth: str = "5/minute"`, before `class Config:`):

```python
    # Groq LLM (free-tier budgets per organisation key)
    groq_api_key_1: Optional[str] = None
    groq_api_key_2: Optional[str] = None
    groq_api_key_3: Optional[str] = None
    groq_model: str = "openai/gpt-oss-120b"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_rpm_per_key: int = 25
    groq_rpd_per_key: int = 900
    groq_tpm_per_key: int = 7000
    groq_tpd_per_key: int = 180000
    groq_max_wait_seconds: int = 60
    groq_request_timeout_seconds: int = 30
    groq_reasoning_effort: str = "low"
    groq_llm_enabled: bool = False
```

- [ ] **Step 2: Write the failing limiter test**

Create `backend/tests/llm/__init__.py` as an empty file.

Create `backend/tests/llm/test_in_memory_limiter.py`:

```python
import pytest

from backend.services.llm.limiter import Budgets, InMemoryRateLimiter


class FakeClock:
    def __init__(self, now_ms: int = 1_000_000):
        self.now_ms = now_ms

    def __call__(self) -> int:
        return self.now_ms

    def advance(self, ms: int) -> None:
        self.now_ms += ms


def _limiter(rpm=10, rpd=100, tpm=1000, tpd=10000):
    clock = FakeClock()
    budgets = Budgets(rpm=rpm, rpd=rpd, tpm=tpm, tpd=tpd)
    return InMemoryRateLimiter(budgets, clock=clock), clock


async def test_reserve_succeeds_within_budget():
    limiter, _ = _limiter()
    result = await limiter.reserve("kh", 100)
    assert result.reservation is not None
    assert result.reservation.tokens == 100
    assert result.wait_ms == 0


async def test_request_budget_denies_and_reports_wait_until_oldest_expires():
    limiter, clock = _limiter(rpm=2)
    await limiter.reserve("kh", 10)
    clock.advance(10_000)
    await limiter.reserve("kh", 10)
    clock.advance(5_000)
    denied = await limiter.reserve("kh", 10)
    assert denied.reservation is None
    assert denied.reason == "minute_requests"
    assert denied.wait_ms == 45_000


async def test_token_budget_denies_even_with_request_slots_free():
    limiter, _ = _limiter(rpm=100, tpm=250)
    assert (await limiter.reserve("kh", 200)).reservation is not None
    denied = await limiter.reserve("kh", 100)
    assert denied.reservation is None
    assert denied.reason == "minute_tokens"


async def test_settle_refunds_unused_reservation():
    limiter, _ = _limiter(tpm=250)
    result = await limiter.reserve("kh", 200)
    await limiter.settle(result.reservation, actual_tokens=50)
    again = await limiter.reserve("kh", 200)
    assert again.reservation is not None


async def test_settle_records_overage_so_the_next_call_waits():
    limiter, _ = _limiter(tpm=300)
    result = await limiter.reserve("kh", 100)
    await limiter.settle(result.reservation, actual_tokens=250)
    denied = await limiter.reserve("kh", 100)
    assert denied.reservation is None
    assert denied.reason == "minute_tokens"


async def test_settle_to_zero_releases_all_reserved_tokens():
    limiter, _ = _limiter(tpm=100)
    result = await limiter.reserve("kh", 100)
    await limiter.settle(result.reservation, actual_tokens=0)
    again = await limiter.reserve("kh", 100)
    assert again.reservation is not None


async def test_minute_window_slides_past_old_requests():
    limiter, clock = _limiter(rpm=1)
    await limiter.reserve("kh", 10)
    clock.advance(60_001)
    again = await limiter.reserve("kh", 10)
    assert again.reservation is not None


async def test_daily_request_budget_outlives_the_minute_window():
    limiter, clock = _limiter(rpm=10, rpd=2)
    await limiter.reserve("kh", 10)
    await limiter.reserve("kh", 10)
    clock.advance(61_000)
    denied = await limiter.reserve("kh", 10)
    assert denied.reservation is None
    assert denied.reason == "daily"


async def test_daily_token_budget_counts_settled_usage():
    limiter, clock = _limiter(rpd=100, tpm=1000, tpd=1000)
    first = await limiter.reserve("kh", 700)
    await limiter.settle(first.reservation, actual_tokens=700)
    clock.advance(61_000)
    denied = await limiter.reserve("kh", 700)
    assert denied.reservation is None
    assert denied.reason == "daily"


async def test_block_makes_the_key_unavailable_until_it_lapses():
    limiter, clock = _limiter()
    await limiter.block("kh", seconds=5)
    denied = await limiter.reserve("kh", 10)
    assert denied.reservation is None
    assert denied.reason == "blocked"
    assert denied.wait_ms == 5_000
    clock.advance(5_001)
    assert (await limiter.reserve("kh", 10)).reservation is not None


async def test_keys_are_isolated_from_each_other():
    limiter, _ = _limiter(rpm=1)
    assert (await limiter.reserve("a", 10)).reservation is not None
    assert (await limiter.reserve("b", 10)).reservation is not None
    assert (await limiter.reserve("a", 10)).reservation is None
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `$env:REDIS_PORT='6380'; & "D:\python\project\StudentHub\venv\Scripts\python.exe" -m pytest backend/tests/llm/test_in_memory_limiter.py -v`

Expected: collection error, `ModuleNotFoundError: No module named 'backend.services.llm'`.

- [ ] **Step 4: Write the limiter module**

Create `backend/services/llm/__init__.py`:

```python
from .limiter import Budgets, InMemoryRateLimiter, RateLimiter, Reservation, ReserveResult

__all__ = [
    "Budgets",
    "InMemoryRateLimiter",
    "RateLimiter",
    "Reservation",
    "ReserveResult",
]
```

Create `backend/services/llm/limiter.py`:

```python
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Protocol, Tuple

_MINUTE_MS = 60_000
_HOUR_MS = 3_600_000
_DAY_BUCKETS = 25
_DAY_MS = _DAY_BUCKETS * _HOUR_MS


@dataclass(frozen=True)
class Budgets:
    rpm: int
    rpd: int
    tpm: int
    tpd: int


@dataclass(frozen=True)
class Reservation:
    keyhash: str
    request_id: str
    tokens: int
    at_ms: int


@dataclass(frozen=True)
class ReserveResult:
    reservation: Optional[Reservation]
    wait_ms: int
    reason: str


class RateLimiter(Protocol):
    async def reserve(self, keyhash: str, tokens: int) -> ReserveResult:
        ...

    async def settle(self, reservation: Reservation, actual_tokens: int) -> None:
        ...

    async def block(self, keyhash: str, seconds: float) -> None:
        ...


def _wall_clock_ms() -> int:
    return int(time.time() * 1000)


class InMemoryRateLimiter:
    def __init__(self, budgets: Budgets, clock: Optional[Callable[[], int]] = None):
        self._budgets = budgets
        self._clock = clock or _wall_clock_ms
        self._requests: Dict[str, List[Tuple[int, str]]] = {}
        self._tokens: Dict[str, List[Tuple[int, str, int]]] = {}
        self._day_requests: Dict[str, Dict[int, int]] = {}
        self._day_tokens: Dict[str, Dict[int, int]] = {}
        self._blocked_until: Dict[str, int] = {}
        self._counter = 0

    async def reserve(self, keyhash: str, tokens: int) -> ReserveResult:
        now = self._clock()
        blocked = self._blocked_until.get(keyhash, 0)
        if blocked > now:
            return ReserveResult(None, blocked - now, "blocked")

        self._purge(keyhash, now)
        minute_requests, minute_tokens = self._minute_usage(keyhash, now)
        day_requests, day_tokens = self._day_usage(keyhash, now)
        budgets = self._budgets

        if minute_requests + 1 > budgets.rpm:
            return ReserveResult(None, self._next_minute_expiry(keyhash, now), "minute_requests")
        if minute_tokens + tokens > budgets.tpm:
            return ReserveResult(None, self._next_minute_expiry(keyhash, now), "minute_tokens")
        if day_requests + 1 > budgets.rpd or day_tokens + tokens > budgets.tpd:
            return ReserveResult(None, self._next_day_expiry(keyhash, now), "daily")

        self._counter += 1
        request_id = f"r{self._counter}"
        self._requests.setdefault(keyhash, []).append((now, request_id))
        self._tokens.setdefault(keyhash, []).append((now, request_id, tokens))
        hour = now // _HOUR_MS
        requests = self._day_requests.setdefault(keyhash, {})
        tokens_by_hour = self._day_tokens.setdefault(keyhash, {})
        requests[hour] = requests.get(hour, 0) + 1
        tokens_by_hour[hour] = tokens_by_hour.get(hour, 0) + tokens
        return ReserveResult(Reservation(keyhash, request_id, tokens, now), 0, "ok")

    async def settle(self, reservation: Reservation, actual_tokens: int) -> None:
        entries = self._tokens.get(reservation.keyhash, [])
        for index, (at_ms, request_id, reserved) in enumerate(entries):
            if request_id != reservation.request_id:
                continue
            delta = max(0, actual_tokens) - reserved
            entries[index] = (at_ms, request_id, max(0, actual_tokens))
            if delta:
                hour = at_ms // _HOUR_MS
                tokens_by_hour = self._day_tokens.setdefault(reservation.keyhash, {})
                tokens_by_hour[hour] = max(0, tokens_by_hour.get(hour, 0) + delta)
            return

    async def block(self, keyhash: str, seconds: float) -> None:
        self._blocked_until[keyhash] = self._clock() + int(seconds * 1000)

    def _purge(self, keyhash: str, now: int) -> None:
        cutoff = now - _MINUTE_MS
        self._requests[keyhash] = [
            entry for entry in self._requests.get(keyhash, []) if entry[0] > cutoff
        ]
        self._tokens[keyhash] = [
            entry for entry in self._tokens.get(keyhash, []) if entry[0] > cutoff
        ]
        horizon = now // _HOUR_MS - (_DAY_BUCKETS - 1)
        for table in (self._day_requests, self._day_tokens):
            buckets = table.get(keyhash)
            if not buckets:
                continue
            for hour in [h for h in buckets if h < horizon]:
                del buckets[hour]

    def _minute_usage(self, keyhash: str, now: int) -> Tuple[int, int]:
        cutoff = now - _MINUTE_MS
        requests = sum(1 for entry in self._requests.get(keyhash, []) if entry[0] > cutoff)
        tokens = sum(
            entry[2] for entry in self._tokens.get(keyhash, []) if entry[0] > cutoff
        )
        return requests, tokens

    def _day_usage(self, keyhash: str, now: int) -> Tuple[int, int]:
        lowest = now // _HOUR_MS - (_DAY_BUCKETS - 1)
        requests = sum(
            count
            for hour, count in self._day_requests.get(keyhash, {}).items()
            if hour >= lowest
        )
        tokens = sum(
            count
            for hour, count in self._day_tokens.get(keyhash, {}).items()
            if hour >= lowest
        )
        return requests, tokens

    def _next_minute_expiry(self, keyhash: str, now: int) -> int:
        entries = self._requests.get(keyhash, [])
        if not entries:
            return _MINUTE_MS
        oldest = min(entry[0] for entry in entries)
        return max(1, oldest + _MINUTE_MS - now)

    def _next_day_expiry(self, keyhash: str, now: int) -> int:
        buckets = list(self._day_requests.get(keyhash, {}))
        buckets += list(self._day_tokens.get(keyhash, {}))
        if not buckets:
            return _DAY_MS
        oldest = min(buckets)
        return max(1, (oldest + _DAY_BUCKETS) * _HOUR_MS - now)
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `$env:REDIS_PORT='6380'; & "D:\python\project\StudentHub\venv\Scripts\python.exe" -m pytest backend/tests/llm/test_in_memory_limiter.py -v`

Expected: 11 passed.

- [ ] **Step 6: Verify the existing suite is untouched**

Run: `$env:REDIS_PORT='6380'; & "D:\python\project\StudentHub\venv\Scripts\python.exe" -m pytest backend/tests/interview_engine -q`

Expected: 179 passed.

- [ ] **Step 7: Commit**

```powershell
git add -- backend/config.py backend/services/llm/__init__.py backend/services/llm/limiter.py backend/tests/llm/__init__.py backend/tests/llm/test_in_memory_limiter.py
git commit -m "feat(llm): add rate-limiter contracts and in-memory limiter"
```

---

### Task 2: Redis limiter and the Redis-down fallback

**Files:**
- Create: `backend/services/llm/redis_limiter.py`
- Create: `backend/tests/llm/test_redis_limiter.py`
- Modify: `backend/services/llm/__init__.py` (re-export)

**Interfaces:**
- Consumes: `Budgets`, `Reservation`, `ReserveResult`, `RateLimiter`, `InMemoryRateLimiter` from Task 1.
- Produces:
  - `RedisRateLimiter(redis, budgets: Budgets, clock: Callable[[], int] | None = None)`.
  - `FallbackRateLimiter(primary, fallback, logger=None)` — same `RateLimiter` surface; logs once on first degradation.
  - Redis key layout `llm:rl:{keyhash}:min|tokens|tokamt|day|daytok|block`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/llm/test_redis_limiter.py`:

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `$env:REDIS_PORT='6380'; & "D:\python\project\StudentHub\venv\Scripts\python.exe" -m pytest backend/tests/llm/test_redis_limiter.py -v`

Expected: collection error, `ModuleNotFoundError: No module named 'backend.services.llm.redis_limiter'`.

- [ ] **Step 3: Implement the Redis limiter**

Create `backend/services/llm/redis_limiter.py`:

```python
import logging
import time
import uuid
from typing import Callable, Optional

from .limiter import Budgets, InMemoryRateLimiter, Reservation, ReserveResult

logger = logging.getLogger(__name__)

_MINUTE_MS = 60_000
_HOUR_MS = 3_600_000

_RESERVE = """
local now = tonumber(ARGV[1])
local rid = ARGV[2]
local tokens = tonumber(ARGV[3])
local rpm = tonumber(ARGV[4])
local rpd = tonumber(ARGV[5])
local tpm = tonumber(ARGV[6])
local tpd = tonumber(ARGV[7])
local hour = tonumber(ARGV[8])
local minute_ms = 60000
local day_buckets = 25

local blocked = redis.call('PTTL', KEYS[6])
if blocked > 0 then
  return {0, blocked, 'blocked'}
end

redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now - minute_ms)
local minute_requests = redis.call('ZCARD', KEYS[1])

redis.call('ZREMRANGEBYSCORE', KEYS[2], '-inf', now - minute_ms)
local members = redis.call('ZRANGE', KEYS[2], 0, -1)
local minute_tokens = 0
for _, member in ipairs(members) do
  minute_tokens = minute_tokens + tonumber(redis.call('HGET', KEYS[3], member) or '0')
end

local day_requests = 0
local day_tokens = 0
for i = 0, day_buckets - 1 do
  local bucket = tostring(hour - i)
  day_requests = day_requests + tonumber(redis.call('HGET', KEYS[4], bucket) or '0')
  day_tokens = day_tokens + tonumber(redis.call('HGET', KEYS[5], bucket) or '0')
end

if minute_requests + 1 > rpm then
  local oldest = redis.call('ZRANGE', KEYS[1], 0, 0, 'WITHSCORES')
  local wait = minute_ms
  if oldest[2] then
    wait = tonumber(oldest[2]) + minute_ms - now
  end
  if wait < 1 then wait = 1 end
  return {0, wait, 'minute_requests'}
end

if minute_tokens + tokens > tpm then
  local oldest = redis.call('ZRANGE', KEYS[2], 0, 0, 'WITHSCORES')
  local wait = minute_ms
  if oldest[2] then
    wait = tonumber(oldest[2]) + minute_ms - now
  end
  if wait < 1 then wait = 1 end
  return {0, wait, 'minute_tokens'}
end

if day_requests + 1 > rpd or day_tokens + tokens > tpd then
  return {0, 86400000, 'daily'}
end

redis.call('ZADD', KEYS[1], now, rid)
redis.call('ZADD', KEYS[2], now, rid)
redis.call('HSET', KEYS[3], rid, tokens)
redis.call('HINCRBY', KEYS[4], hour, 1)
redis.call('HINCRBY', KEYS[5], hour, tokens)
redis.call('PEXPIRE', KEYS[1], 120000)
redis.call('PEXPIRE', KEYS[2], 120000)
redis.call('PEXPIRE', KEYS[3], 120000)
redis.call('PEXPIRE', KEYS[4], 93600000)
redis.call('PEXPIRE', KEYS[5], 93600000)
return {1, 0, rid}
"""

_SETTLE = """
local rid = ARGV[1]
local reserved = tonumber(ARGV[2])
local actual = tonumber(ARGV[3])
local hour = ARGV[4]
if actual <= 0 then
  redis.call('HDEL', KEYS[1], rid)
else
  redis.call('HSET', KEYS[1], rid, actual)
end
local delta = actual - reserved
if delta ~= 0 then
  local updated = redis.call('HINCRBY', KEYS[2], hour, delta)
  if updated < 0 then
    redis.call('HSET', KEYS[2], hour, 0)
  end
  redis.call('PEXPIRE', KEYS[2], 93600000)
end
return 1
"""

_KEY_PREFIX = "llm:rl:{keyhash}:"


def _wall_clock_ms() -> int:
    return int(time.time() * 1000)


class RedisRateLimiter:
    def __init__(self, redis, budgets: Budgets, clock: Optional[Callable[[], int]] = None):
        self._redis = redis
        self._budgets = budgets
        self._clock = clock or _wall_clock_ms

    def _keys(self, keyhash: str):
        prefix = _KEY_PREFIX.format(keyhash=keyhash)
        return [
            f"{prefix}min",
            f"{prefix}tokens",
            f"{prefix}tokamt",
            f"{prefix}day",
            f"{prefix}daytok",
            f"{prefix}block",
        ]

    async def reserve(self, keyhash: str, tokens: int) -> ReserveResult:
        now = self._clock()
        request_id = uuid.uuid4().hex
        budgets = self._budgets
        reply = await self._redis.eval(
            _RESERVE,
            6,
            *self._keys(keyhash),
            now,
            request_id,
            tokens,
            budgets.rpm,
            budgets.rpd,
            budgets.tpm,
            budgets.tpd,
            now // _HOUR_MS,
        )
        allowed, wait_ms, reason = reply
        if int(allowed) == 1:
            return ReserveResult(Reservation(keyhash, request_id, tokens, now), 0, "ok")
        return ReserveResult(None, int(wait_ms), str(reason))

    async def settle(self, reservation: Reservation, actual_tokens: int) -> None:
        actual = max(0, actual_tokens)
        keys = self._keys(reservation.keyhash)
        await self._redis.eval(
            _SETTLE,
            2,
            keys[2],
            keys[4],
            reservation.request_id,
            reservation.tokens,
            actual,
            reservation.at_ms // _HOUR_MS,
        )

    async def block(self, keyhash: str, seconds: float) -> None:
        await self._redis.set(
            f"{_KEY_PREFIX.format(keyhash=keyhash)}block",
            "1",
            px=max(1, int(seconds * 1000)),
        )


class FallbackRateLimiter:
    def __init__(self, primary, fallback, logger=None):
        self._primary = primary
        self._fallback = fallback
        self._logger = logger or logging.getLogger(__name__)
        self._degraded = False

    async def reserve(self, keyhash: str, tokens: int) -> ReserveResult:
        try:
            return await self._primary.reserve(keyhash, tokens)
        except Exception as exc:
            self._degrade(exc)
            return await self._fallback.reserve(keyhash, tokens)

    async def settle(self, reservation: Reservation, actual_tokens: int) -> None:
        try:
            await self._primary.settle(reservation, actual_tokens)
        except Exception as exc:
            self._degrade(exc)
            await self._fallback.settle(reservation, actual_tokens)

    async def block(self, keyhash: str, seconds: float) -> None:
        try:
            await self._primary.block(keyhash, seconds)
        except Exception as exc:
            self._degrade(exc)
            await self._fallback.block(keyhash, seconds)

    def _degrade(self, exc: Exception) -> None:
        if not self._degraded:
            self._degraded = True
            self._logger.warning(
                "LLM rate limiter degraded to in-memory enforcement: %s", exc
            )
```

- [ ] **Step 4: Re-export from the package**

Replace `backend/services/llm/__init__.py` with:

```python
from .limiter import Budgets, InMemoryRateLimiter, RateLimiter, Reservation, ReserveResult
from .redis_limiter import FallbackRateLimiter, RedisRateLimiter

__all__ = [
    "Budgets",
    "FallbackRateLimiter",
    "InMemoryRateLimiter",
    "RateLimiter",
    "RedisRateLimiter",
    "Reservation",
    "ReserveResult",
]
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `$env:REDIS_PORT='6380'; & "D:\python\project\StudentHub\venv\Scripts\python.exe" -m pytest backend/tests/llm/test_redis_limiter.py -v`

Expected: 4 passed (2 real-Redis tests, 2 fallback tests). If Redis is unreachable the two real tests skip and 2 pass; start `studenthub-redis` on 6380 and re-run.

- [ ] **Step 6: Commit**

```powershell
git add -- backend/services/llm/__init__.py backend/services/llm/redis_limiter.py backend/tests/llm/test_redis_limiter.py
git commit -m "feat(llm): add atomic Redis limiter and in-memory fallback"
```

---

### Task 3: Key pool and fingerprints

**Files:**
- Create: `backend/services/llm/keys.py`
- Create: `backend/tests/llm/test_keys.py`
- Modify: `backend/services/llm/__init__.py` (re-export)

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `fingerprint(value: str) -> str` — `sha256(value)[:16]`.
  - `ApiKey` frozen dataclass with `index: int`, `value: str` (excluded from `repr`), `keyhash: str`.
  - `ApiKeyPool(keys: Sequence[str])` with `__len__`, `__iter__` yielding `ApiKey`, `empty: bool`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/llm/test_keys.py`:

```python
from backend.services.llm.keys import ApiKeyPool, fingerprint


def test_fingerprint_is_stable_and_short():
    value = "gsk_example_key_value"
    assert fingerprint(value) == fingerprint(value)
    assert len(fingerprint(value)) == 16


def test_fingerprint_does_not_contain_the_raw_key():
    value = "gsk_supersecret"
    assert value not in fingerprint(value)


def test_pool_skips_blank_keys_and_numbers_the_rest():
    pool = ApiKeyPool(["gsk_a", "", "   ", "gsk_b"])
    assert len(pool) == 2
    assert [key.index for key in pool] == [0, 1]
    assert [key.value for key in pool] == ["gsk_a", "gsk_b"]


def test_pool_is_empty_when_nothing_is_configured():
    pool = ApiKeyPool([None, "", "  "])
    assert pool.empty is True
    assert len(pool) == 0


def test_key_repr_never_leaks_the_value():
    pool = ApiKeyPool(["gsk_supersecret"])
    key = list(pool)[0]
    assert "gsk_supersecret" not in repr(key)
    assert key.keyhash in repr(key)


def test_pool_gives_each_key_a_distinct_fingerprint():
    pool = ApiKeyPool(["gsk_a", "gsk_b", "gsk_c"])
    hashes = {key.keyhash for key in pool}
    assert len(hashes) == 3
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `$env:REDIS_PORT='6380'; & "D:\python\project\StudentHub\venv\Scripts\python.exe" -m pytest backend/tests/llm/test_keys.py -v`

Expected: collection error, `No module named 'backend.services.llm.keys'`.

- [ ] **Step 3: Implement the key pool**

Create `backend/services/llm/keys.py`:

```python
import hashlib
from dataclasses import dataclass, field
from typing import Iterator, Optional, Sequence


def fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class ApiKey:
    index: int
    value: str = field(repr=False)
    keyhash: str


class ApiKeyPool:
    def __init__(self, keys: Sequence[Optional[str]]):
        cleaned = [key.strip() for key in keys if key and key.strip()]
        self._keys = tuple(
            ApiKey(index=index, value=value, keyhash=fingerprint(value))
            for index, value in enumerate(cleaned)
        )

    def __len__(self) -> int:
        return len(self._keys)

    def __iter__(self) -> Iterator[ApiKey]:
        return iter(self._keys)

    @property
    def empty(self) -> bool:
        return not self._keys
```

- [ ] **Step 4: Re-export and run**

Add to `backend/services/llm/__init__.py`:

```python
from .keys import ApiKey, ApiKeyPool, fingerprint
```

and append `"ApiKey"`, `"ApiKeyPool"`, `"fingerprint"` to `__all__`.

Run: `$env:REDIS_PORT='6380'; & "D:\python\project\StudentHub\venv\Scripts\python.exe" -m pytest backend/tests/llm/test_keys.py -v`

Expected: 6 passed.

- [ ] **Step 5: Commit**

```powershell
git add -- backend/services/llm/__init__.py backend/services/llm/keys.py backend/tests/llm/test_keys.py
git commit -m "feat(llm): add API key pool with non-reversible fingerprints"
```

---

### Task 4: Groq client with reservation, settlement, rotation and 429 handling

**Files:**
- Create: `backend/services/llm/groq.py`
- Create: `backend/tests/llm/test_groq_client.py`
- Modify: `backend/services/llm/__init__.py` (re-export)

**Interfaces:**
- Consumes: `ApiKeyPool` (Task 3), `RateLimiter`/`ReserveResult`/`Reservation` (Task 1).
- Produces:
  - `LLMUnavailable(reason: str)` with `.reason`.
  - `LLMCompletion(text: str, prompt_tokens: int, completion_tokens: int, keyhash: str, model: str)`.
  - `estimate_tokens(*texts: str) -> int`.
  - `GroqLLMClient(pool, limiter, *, model, base_url, request_timeout_seconds, max_wait_seconds, reasoning_effort="low", max_attempts=6, client_factory=None, clock=None, sleep=None)` with
    `async complete(*, system, user, max_completion_tokens, temperature=0.2, response_format=None) -> LLMCompletion`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/llm/test_groq_client.py`:

```python
import asyncio
from types import SimpleNamespace

import pytest

from backend.services.llm.groq import (
    GroqLLMClient,
    LLMUnavailable,
    estimate_tokens,
)
from backend.services.llm.keys import ApiKeyPool
from backend.services.llm.limiter import Budgets, InMemoryRateLimiter, Reservation, ReserveResult


class FakeClock:
    def __init__(self, now_ms: int = 1_000_000):
        self.now_ms = now_ms

    def __call__(self) -> int:
        return self.now_ms

    def advance(self, ms: int) -> None:
        self.now_ms += ms


class NoSleep:
    def __init__(self, clock: FakeClock):
        self._clock = clock

    async def __call__(self, seconds: float) -> None:
        self._clock.advance(int(seconds * 1000))


class FakeCompletions:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class FakeClient:
    def __init__(self, outcomes):
        self.chat = SimpleNamespace(completions=FakeCompletions(outcomes))


def _response(text, prompt_tokens=10, completion_tokens=20, finish_reason="stop"):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text), finish_reason=finish_reason)],
        usage=SimpleNamespace(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        ),
    )


def _client(outcomes, budgets=None, clock=None, keys=("gsk_a",), max_wait=60, sleep=None):
    clock = clock or FakeClock()
    budgets = budgets or Budgets(rpm=10, rpd=100, tpm=100000, tpd=1000000)
    limiter = InMemoryRateLimiter(budgets, clock=clock)
    fake = FakeClient(outcomes)
    client = GroqLLMClient(
        ApiKeyPool(list(keys)),
        limiter,
        model="openai/gpt-oss-120b",
        base_url="https://example.invalid/openai/v1",
        request_timeout_seconds=5,
        max_wait_seconds=max_wait,
        client_factory=lambda api_key: fake,
        clock=clock,
        sleep=sleep or NoSleep(clock),
    )
    return client, fake, clock, limiter


async def test_estimate_tokens_is_monotonic_and_positive():
    assert estimate_tokens("") >= 1
    assert estimate_tokens("abcd") >= 1
    assert estimate_tokens("a" * 4000) > estimate_tokens("a" * 40)


async def test_complete_returns_text_and_usage():
    client, fake, _, _ = _client([_response("hello")])
    completion = await client.complete(system="s", user="u", max_completion_tokens=100)
    assert completion.text == "hello"
    assert completion.prompt_tokens == 10
    assert completion.completion_tokens == 20
    assert completion.model == "openai/gpt-oss-120b"
    kwargs = fake.chat.completions.calls[0]
    assert kwargs["max_completion_tokens"] == 100
    assert "max_tokens" not in kwargs
    assert kwargs["reasoning_effort"] == "low"


async def test_complete_passes_json_mode_when_requested():
    client, fake, _, _ = _client([_response('{"ok": true}')])
    await client.complete(
        system="s", user="u", max_completion_tokens=100, response_format="json_object"
    )
    assert fake.chat.completions.calls[0]["response_format"] == {"type": "json_object"}


async def test_complete_raises_when_no_key_is_configured():
    clock = FakeClock()
    limiter = InMemoryRateLimiter(Budgets(10, 100, 1000, 10000), clock=clock)
    client = GroqLLMClient(
        ApiKeyPool([]),
        limiter,
        model="m",
        base_url="https://example.invalid",
        request_timeout_seconds=5,
        max_wait_seconds=1,
        client_factory=lambda api_key: FakeClient([]),
        clock=clock,
        sleep=NoSleep(clock),
    )
    with pytest.raises(LLMUnavailable) as caught:
        await client.complete(system="s", user="u", max_completion_tokens=10)
    assert caught.value.reason == "no_api_key"


async def test_complete_fails_when_the_wait_budget_is_exceeded():
    clock = FakeClock()
    client, _, _, _ = _client(
        [_response("unused")],
        budgets=Budgets(rpm=0, rpd=100, tpm=1000, tpd=10000),
        clock=clock,
        max_wait=0,
    )
    with pytest.raises(LLMUnavailable) as caught:
        await client.complete(system="s", user="u", max_completion_tokens=10)
    assert caught.value.reason == "wait_budget_exceeded"


async def test_truncated_response_is_a_typed_failure():
    client, _, _, _ = _client([_response("{\"partial\": ", finish_reason="length")])
    with pytest.raises(LLMUnavailable) as caught:
        await client.complete(system="s", user="u", max_completion_tokens=10)
    assert caught.value.reason == "truncated"


async def test_429_rotates_to_the_next_key_and_blocks_the_first():
    rate_limited = Exception("429 rate limited")
    rate_limited.status_code = 429
    rate_limited.response = SimpleNamespace(headers={"retry-after": "30"})

    client, fake, clock, limiter = _client(
        [rate_limited, _response("second key")],
        keys=("gsk_a", "gsk_b"),
    )
    completion = await client.complete(system="s", user="u", max_completion_tokens=10)
    assert completion.text == "second key"
    assert len(fake.chat.completions.calls) == 2


async def test_transport_error_refunds_the_reservation_and_fails():
    client, _, _, limiter = _client([RuntimeError("connection reset")], budgets=Budgets(10, 100, 100, 10000))
    with pytest.raises(LLMUnavailable) as caught:
        await client.complete(system="s", user="u", max_completion_tokens=10)
    assert caught.value.reason == "transport_error"
    result = await limiter.reserve("unrelated", 100)
    assert result.reservation is not None


async def test_successful_call_never_leaks_the_key_into_a_log(monkeypatch):
    logged = []

    import backend.services.llm.groq as groq_module

    class RecordingLogger:
        def info(self, message, *args, **kwargs):
            logged.append(str(message) + str(args))

        def warning(self, message, *args, **kwargs):
            logged.append(str(message) + str(args))

        def exception(self, message, *args, **kwargs):
            logged.append(str(message) + str(args))

    monkeypatch.setattr(groq_module, "logger", RecordingLogger())
    client, _, _, _ = _client([_response("ok")], keys=("gsk_supersecret_value",))
    await client.complete(system="s", user="u", max_completion_tokens=10)
    assert all("gsk_supersecret_value" not in entry for entry in logged)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `$env:REDIS_PORT='6380'; & "D:\python\project\StudentHub\venv\Scripts\python.exe" -m pytest backend/tests/llm/test_groq_client.py -v`

Expected: collection error, `No module named 'backend.services.llm.groq'`.

- [ ] **Step 3: Implement the client**

Create `backend/services/llm/groq.py`:

```python
import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Callable, Optional

from .keys import ApiKey, ApiKeyPool
from .limiter import RateLimiter, Reservation

logger = logging.getLogger(__name__)

_MAX_ATTEMPTS = 6


class LLMUnavailable(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class LLMCompletion:
    text: str
    prompt_tokens: int
    completion_tokens: int
    keyhash: str
    model: str


def estimate_tokens(*texts: str) -> int:
    characters = sum(len(text) for text in texts) + 8
    return max(1, (characters + 3) // 4)


def _wall_clock_ms() -> int:
    return int(time.time() * 1000)


def _retry_after_seconds(exc: Exception) -> Optional[float]:
    if getattr(exc, "status_code", None) != 429:
        return None
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None) or {}
    raw = headers.get("retry-after") or headers.get("Retry-After")
    try:
        return float(raw) if raw is not None else 2.0
    except (TypeError, ValueError):
        return 2.0


class GroqLLMClient:
    def __init__(
        self,
        pool: ApiKeyPool,
        limiter: RateLimiter,
        *,
        model: str,
        base_url: str,
        request_timeout_seconds: float,
        max_wait_seconds: float,
        reasoning_effort: str = "low",
        max_attempts: int = _MAX_ATTEMPTS,
        client_factory: Optional[Callable[[ApiKey], object]] = None,
        clock: Optional[Callable[[], int]] = None,
        sleep: Optional[Callable[[float], object]] = None,
    ):
        self._pool = pool
        self._limiter = limiter
        self._model = model
        self._base_url = base_url
        self._timeout = request_timeout_seconds
        self._max_wait_seconds = max_wait_seconds
        self._reasoning_effort = reasoning_effort
        self._max_attempts = max_attempts
        self._client_factory = client_factory
        self._clock = clock or _wall_clock_ms
        self._sleep = sleep or asyncio.sleep
        self._clients: dict = {}

    def _client_for(self, api_key: ApiKey):
        client = self._clients.get(api_key.keyhash)
        if client is None:
            if self._client_factory is not None:
                client = self._client_factory(api_key)
            else:
                from openai import AsyncOpenAI

                client = AsyncOpenAI(
                    api_key=api_key.value,
                    base_url=self._base_url,
                    timeout=self._timeout,
                )
            self._clients[api_key.keyhash] = client
        return client

    async def complete(
        self,
        *,
        system: str,
        user: str,
        max_completion_tokens: int,
        temperature: float = 0.2,
        response_format: Optional[str] = None,
    ) -> LLMCompletion:
        if self._pool.empty:
            raise LLMUnavailable("no_api_key")

        reserved = estimate_tokens(system, user) + max_completion_tokens
        deadline_ms = self._clock() + int(self._max_wait_seconds * 1000)
        attempts_left = self._max_attempts

        while attempts_left > 0:
            key, reservation, wait_ms, reason = await self._reserve_any(reserved)
            if reservation is None:
                if reason == "daily":
                    raise LLMUnavailable("daily_exhausted")
                if wait_ms <= 0 or self._clock() + wait_ms > deadline_ms:
                    raise LLMUnavailable("wait_budget_exceeded")
                logger.info(
                    "LLM rate limit reached, waiting %sms (%s)", wait_ms, reason
                )
                await self._sleep(wait_ms / 1000)
                continue

            attempts_left -= 1
            try:
                text, prompt_tokens, completion_tokens = await self._call(
                    key,
                    system=system,
                    user=user,
                    max_completion_tokens=max_completion_tokens,
                    temperature=temperature,
                    response_format=response_format,
                )
            except LLMUnavailable:
                await self._limiter.settle(reservation, 0)
                raise
            except Exception as exc:
                await self._limiter.settle(reservation, 0)
                retry_after = _retry_after_seconds(exc)
                if retry_after is not None:
                    logger.warning(
                        "LLM key %s hit 429, rotating for %.1fs",
                        key.keyhash,
                        retry_after,
                    )
                    await self._limiter.block(key.keyhash, retry_after)
                    continue
                logger.warning("LLM transport failure: %s", type(exc).__name__)
                raise LLMUnavailable("transport_error") from exc

            actual = prompt_tokens + completion_tokens
            await self._limiter.settle(reservation, actual)
            logger.info(
                "LLM call ok key=%s prompt=%s completion=%s",
                key.keyhash,
                prompt_tokens,
                completion_tokens,
            )
            return LLMCompletion(
                text=text,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                keyhash=key.keyhash,
                model=self._model,
            )

        raise LLMUnavailable("attempts_exhausted")

    async def _reserve_any(self, tokens: int):
        best_wait = None
        best_reason = "exhausted"
        for key in self._pool:
            result = await self._limiter.reserve(key.keyhash, tokens)
            if result.reservation is not None:
                return key, result.reservation, 0, "ok"
            if best_wait is None or result.wait_ms < best_wait:
                best_wait = result.wait_ms
                best_reason = result.reason
        return None, None, best_wait or 0, best_reason

    async def _call(
        self,
        key: ApiKey,
        *,
        system: str,
        user: str,
        max_completion_tokens: int,
        temperature: float,
        response_format: Optional[str],
    ):
        kwargs = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_completion_tokens": max_completion_tokens,
            "reasoning_effort": self._reasoning_effort,
        }
        if response_format:
            kwargs["response_format"] = {"type": response_format}

        response = await asyncio.wait_for(
            self._client_for(key).chat.completions.create(**kwargs),
            timeout=self._timeout,
        )
        choice = response.choices[0]
        if getattr(choice, "finish_reason", None) == "length":
            raise LLMUnavailable("truncated")
        usage = response.usage
        return (
            choice.message.content or "",
            int(usage.prompt_tokens or 0),
            int(usage.completion_tokens or 0),
        )
```

The `except LLMUnavailable` branch must come first so a truncated response keeps its
`truncated` reason instead of being rewritten as `transport_error`.

- [ ] **Step 4: Re-export and run the tests**

Add to `backend/services/llm/__init__.py`:

```python
from .groq import GroqLLMClient, LLMCompletion, LLMUnavailable, estimate_tokens
```

and append those four names to `__all__`.

Run: `$env:REDIS_PORT='6380'; & "D:\python\project\StudentHub\venv\Scripts\python.exe" -m pytest backend/tests/llm/test_groq_client.py -v`

Expected: 9 passed.

- [ ] **Step 5: Commit**

```powershell
git add -- backend/services/llm/__init__.py backend/services/llm/groq.py backend/tests/llm/test_groq_client.py
git commit -m "feat(llm): add Groq client with rotation, 429 handling and token settlement"
```

---

### Task 5: Prompts and the three engine adapters

**Files:**
- Create: `backend/services/llm/prompts.py`
- Create: `backend/interview_engine/adapters/llm.py`
- Create: `backend/tests/llm/test_adapters.py`
- Modify: `backend/services/llm/__init__.py` (re-export prompts module is optional; do not add)

**Interfaces:**
- Consumes: `LLMCompletion`, `LLMUnavailable` (Task 4); port types `AnalysisRequest`, `QuestionRequest`, `EvaluationRequest`, `GeneratedQuestion`; contracts `Analysis`, `EvaluatorOutput`.
- Produces:
  - `prompts.ANALYZER_SYSTEM`, `prompts.GENERATOR_SYSTEM`, `prompts.EVALUATOR_SYSTEM` (str constants).
  - `prompts.analyzer_user(request) -> str`, `prompts.generator_user(request) -> str`, `prompts.evaluator_user(request) -> str`.
  - `GroqAnalyzer(client, max_completion_tokens=600, temperature=0.0)`.
  - `GroqQuestionGenerator(client, max_completion_tokens=400, temperature=0.5)`.
  - `GroqEvaluator(client, max_completion_tokens=1200, temperature=0.0)`.
  - `LLMAdapters(analyzer, generator, evaluator)` and `build_llm_adapters(settings, limiter=None, client=None) -> Optional[LLMAdapters]`.

- [ ] **Step 1: Write the failing adapter tests**

Create `backend/tests/llm/test_adapters.py`:

```python
import json

import pytest

from backend.interview_engine.adapters.llm import (
    GroqAnalyzer,
    GroqEvaluator,
    GroqQuestionGenerator,
)
from backend.interview_engine.contracts.records import Analysis
from backend.interview_engine.ports.capabilities import (
    AnalysisRequest,
    BlueprintSlot,
    CompetencyEvaluationInput,
    EvaluationRequest,
    QuestionRequest,
)
from backend.services.llm.groq import LLMCompletion, LLMUnavailable


class FakeLLM:
    def __init__(self, text=None, error=None):
        self.text = text
        self.error = error
        self.calls = []

    async def complete(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return LLMCompletion(
            text=self.text,
            prompt_tokens=1,
            completion_tokens=1,
            keyhash="abc",
            model="m",
        )


def _analysis_request(text="I led the migration."):
    return AnalysisRequest(
        session_id="s1",
        turn_id="t1",
        question_id="q1",
        slot_id="slot-1",
        competency="ownership",
        text=text,
    )


def _question_request(purpose="primary"):
    slot = BlueprintSlot(
        slot_id="slot-1",
        competency="ownership",
        dimension="behavioural",
        difficulty="medium",
        intent="Probe ownership of a hard project.",
        fallback_question="Tell me about a project you owned.",
        follow_up_question="What did you personally decide?",
        clarification_text="Pick one specific project.",
        hint_text="Think about a decision only you could make.",
    )
    return QuestionRequest(
        session_id="s1",
        slot=slot,
        purpose=purpose,
        role="Engineer",
        company="Acme",
        prior_questions=[],
    )


def _evaluation_request():
    return EvaluationRequest(
        session_id="s1",
        report_id="r1",
        role="Engineer",
        company="Acme",
        competencies=[
            CompetencyEvaluationInput(
                competency="ownership",
                level="developing",
                confidence="medium",
                instances=2,
            )
        ],
    )


async def test_analyzer_maps_a_valid_response():
    text = json.dumps(
        {
            "instance": "new",
            "signal": "sufficient",
            "substantively_deficient": False,
            "contradiction": False,
            "limitation": None,
        }
    )
    analyzer = GroqAnalyzer(FakeLLM(text))
    analysis = await analyzer.analyze(_analysis_request())
    assert analysis == Analysis(signal="sufficient", instance="new")


async def test_analyzer_normalises_off_topic_to_same_instance():
    text = json.dumps({"instance": "new", "signal": "off_topic"})
    analysis = await GroqAnalyzer(FakeLLM(text)).analyze(_analysis_request())
    assert analysis.instance == "same"
    assert analysis.signal == "off_topic"


async def test_analyzer_degrades_on_transport_failure():
    analyzer = GroqAnalyzer(FakeLLM(error=LLMUnavailable("daily_exhausted")))
    analysis = await analyzer.analyze(_analysis_request())
    assert analysis.instance == "same"
    assert analysis.signal == "incomplete"
    assert analysis.substantively_deficient is True
    assert analysis.limitation == "analysis_unavailable"


async def test_analyzer_degrades_on_malformed_json():
    analysis = await GroqAnalyzer(FakeLLM("not json")).analyze(_analysis_request())
    assert analysis.signal == "incomplete"
    assert analysis.limitation == "analysis_unavailable"


async def test_analyzer_degrades_on_an_out_of_contract_enum():
    text = json.dumps({"instance": "maybe", "signal": "sufficient"})
    analysis = await GroqAnalyzer(FakeLLM(text)).analyze(_analysis_request())
    assert analysis.instance == "same"
    assert analysis.limitation == "analysis_unavailable"


async def test_generator_returns_generated_text_stripped_of_quotes():
    generator = GroqQuestionGenerator(FakeLLM('"Tell me about a hard decision."'))
    question = await generator.generate(_question_request())
    assert question.text == "Tell me about a hard decision."
    assert question.source == "generated"


async def test_generator_returns_empty_text_when_the_call_fails():
    generator = GroqQuestionGenerator(FakeLLM(error=RuntimeError("boom")))
    question = await generator.generate(_question_request())
    assert question.text == ""
    assert question.source == "fallback"


async def test_generator_requests_plain_text_not_json():
    fake = FakeLLM("Question?")
    await GroqQuestionGenerator(fake).generate(_question_request())
    assert "response_format" not in fake.calls[0]


async def test_evaluator_returns_reasons_and_narrative():
    text = json.dumps(
        {"reasons": {"ownership": ["Owned the migration end to end."]}, "narrative": "Solid."}
    )
    output = await GroqEvaluator(FakeLLM(text)).evaluate(_evaluation_request())
    assert output.narrative == "Solid."
    assert output.reasons == {"ownership": ["Owned the migration end to end."]}


async def test_evaluator_raises_typed_failure_on_transport_error():
    evaluator = GroqEvaluator(FakeLLM(error=LLMUnavailable("wait_budget_exceeded")))
    with pytest.raises(LLMUnavailable):
        await evaluator.evaluate(_evaluation_request())


async def test_evaluator_rejects_an_unknown_competency():
    text = json.dumps({"reasons": {"leadership": ["x"]}, "narrative": "y"})
    with pytest.raises(LLMUnavailable) as caught:
        await GroqEvaluator(FakeLLM(text)).evaluate(_evaluation_request())
    assert caught.value.reason == "malformed_evaluation"


async def test_evaluator_rejects_malformed_json():
    with pytest.raises(LLMUnavailable):
        await GroqEvaluator(FakeLLM("nope")).evaluate(_evaluation_request())


async def test_evaluator_never_invents_scores():
    text = json.dumps(
        {"reasons": {}, "narrative": "n", "score": 99, "final_score": 1}
    )
    output = await GroqEvaluator(FakeLLM(text)).evaluate(_evaluation_request())
    assert not hasattr(output, "score")
    assert output.reasons == {}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `$env:REDIS_PORT='6380'; & "D:\python\project\StudentHub\venv\Scripts\python.exe" -m pytest backend/tests/llm/test_adapters.py -v`

Expected: collection error, `No module named 'backend.interview_engine.adapters.llm'`.

- [ ] **Step 3: Write the prompts**

Create `backend/services/llm/prompts.py`. It holds only the three system prompts and imports nothing, so the infrastructure layer never reaches into `interview_engine`:

```python
ANALYZER_SYSTEM = (
    "You analyse one interview answer for one competency. "
    "Return a JSON object with exactly these keys: "
    '"instance" ("new" or "same"), "signal" ("sufficient", "incomplete" or '
    '"off_topic"), "substantively_deficient" (boolean), "contradiction" '
    '(boolean), and "limitation" (a short string or null). '
    'Use "new" only when the answer supplies concrete evidence not already '
    'captured. An "off_topic" answer must use "instance": "same". '
    "Never invent evidence. Return JSON only."
)

GENERATOR_SYSTEM = (
    "You are a behavioural interviewer. Write exactly one interview question. "
    "Make it specific to the competency and intent, and do not repeat any "
    "question already asked. Return only the question text: no preamble, no "
    "numbering, no quotation marks, no more than 60 words."
)

EVALUATOR_SYSTEM = (
    "You write the narrative section of a behavioural interview report. "
    "Return a JSON object with exactly two keys: "
    '"reasons", an object mapping each supplied competency id to a list of '
    'short evidence-based strings, and "narrative", a short paragraph. '
    "Do not invent scores, levels, or confidence values: they are already "
    "computed and must not be restated as new judgements. Use only the "
    "supplied competency ids. Return JSON only."
)
```

The three user-message builders live in `adapters/llm.py` (Step 4), not here, because
they read engine port objects and this module must stay free of that dependency.

- [ ] **Step 4: Write the adapters**

Create `backend/interview_engine/adapters/llm.py`:

```python
import json
import logging
from typing import Optional

from ...services.llm import prompts
from ...services.llm.groq import LLMUnavailable
from ..contracts.records import Analysis
from ..contracts.report import EvaluatorOutput
from ..ports.capabilities import (
    AnalysisRequest,
    EvaluationRequest,
    GeneratedQuestion,
    QuestionRequest,
)

logger = logging.getLogger(__name__)

_SIGNALS = {"sufficient", "incomplete", "off_topic"}
_INSTANCES = {"new", "same"}
_UNAVAILABLE = "analysis_unavailable"


def _degraded_analysis() -> Analysis:
    return Analysis(
        signal="incomplete",
        instance="same",
        substantively_deficient=True,
        limitation=_UNAVAILABLE,
    )


def _analyzer_user(request: AnalysisRequest) -> str:
    return (
        f"Competency: {request.competency}\n"
        f"Question id: {request.question_id}\n"
        f"Answer:\n{request.text}"
    )


def _generator_user(request: QuestionRequest) -> str:
    prior = "\n".join(f"- {text}" for text in request.prior_questions) or "- none"
    return (
        f"Role: {request.role or 'unspecified'}\n"
        f"Company: {request.company or 'unspecified'}\n"
        f"Competency: {request.slot.competency}\n"
        f"Intent: {request.slot.intent}\n"
        f"Purpose: {request.purpose}\n"
        f"Already asked:\n{prior}"
    )


def _evaluator_user(request: EvaluationRequest) -> str:
    lines = [
        f"- {item.competency}: level={item.level}, confidence={item.confidence}, "
        f"instances={item.instances}, limitations={item.limitations}"
        for item in request.competencies
    ]
    body = "\n".join(lines) or "- none"
    return (
        f"Role: {request.role or 'unspecified'}\n"
        f"Company: {request.company or 'unspecified'}\n"
        f"Competencies:\n{body}"
    )


def _parse_analysis(text: str) -> Analysis:
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("analysis must be an object")
    instance = data.get("instance")
    signal = data.get("signal")
    if instance not in _INSTANCES or signal not in _SIGNALS:
        raise ValueError("analysis is out of contract")
    if signal == "off_topic":
        instance = "same"
    limitation = data.get("limitation")
    if limitation is not None and not isinstance(limitation, str):
        raise ValueError("limitation must be a string or null")
    return Analysis(
        signal=signal,
        instance=instance,
        contradiction=bool(data.get("contradiction", False)),
        substantively_deficient=bool(data.get("substantively_deficient", False)),
        limitation=limitation,
    )


def _parse_evaluation(text: str, request: EvaluationRequest) -> EvaluatorOutput:
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise LLMUnavailable("malformed_evaluation") from exc
    if not isinstance(data, dict):
        raise LLMUnavailable("malformed_evaluation")
    raw_reasons = data.get("reasons", {})
    if not isinstance(raw_reasons, dict):
        raise LLMUnavailable("malformed_evaluation")
    known = {item.competency for item in request.competencies}
    reasons = {}
    for competency, values in raw_reasons.items():
        if competency not in known:
            raise LLMUnavailable("malformed_evaluation")
        if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
            raise LLMUnavailable("malformed_evaluation")
        reasons[competency] = values
    narrative = data.get("narrative", "")
    if not isinstance(narrative, str):
        raise LLMUnavailable("malformed_evaluation")
    return EvaluatorOutput(reasons=reasons, narrative=narrative)


class GroqAnalyzer:
    def __init__(self, client, max_completion_tokens: int = 600, temperature: float = 0.0):
        self._client = client
        self._max_completion_tokens = max_completion_tokens
        self._temperature = temperature

    async def analyze(self, request: AnalysisRequest) -> Analysis:
        try:
            completion = await self._client.complete(
                system=prompts.ANALYZER_SYSTEM,
                user=_analyzer_user(request),
                max_completion_tokens=self._max_completion_tokens,
                temperature=self._temperature,
                response_format="json_object",
            )
            return _parse_analysis(completion.text)
        except Exception:
            logger.warning("analyzer unavailable, degrading turn", exc_info=True)
            return _degraded_analysis()


class GroqQuestionGenerator:
    def __init__(self, client, max_completion_tokens: int = 400, temperature: float = 0.5):
        self._client = client
        self._max_completion_tokens = max_completion_tokens
        self._temperature = temperature

    async def generate(self, request: QuestionRequest) -> GeneratedQuestion:
        try:
            completion = await self._client.complete(
                system=prompts.GENERATOR_SYSTEM,
                user=_generator_user(request),
                max_completion_tokens=self._max_completion_tokens,
                temperature=self._temperature,
            )
        except Exception:
            logger.warning("question generation unavailable", exc_info=True)
            return GeneratedQuestion(text="", source="fallback")
        text = completion.text.strip().strip('"').strip()
        return GeneratedQuestion(text=text, source="generated")


class GroqEvaluator:
    def __init__(self, client, max_completion_tokens: int = 1200, temperature: float = 0.0):
        self._client = client
        self._max_completion_tokens = max_completion_tokens
        self._temperature = temperature

    async def evaluate(self, request: EvaluationRequest) -> EvaluatorOutput:
        completion = await self._client.complete(
            system=prompts.EVALUATOR_SYSTEM,
            user=_evaluator_user(request),
            max_completion_tokens=self._max_completion_tokens,
            temperature=self._temperature,
            response_format="json_object",
        )
        return _parse_evaluation(completion.text, request)


class LLMAdapters:
    def __init__(self, analyzer, generator, evaluator):
        self.analyzer = analyzer
        self.generator = generator
        self.evaluator = evaluator


def build_llm_adapters(settings, limiter=None, client=None) -> Optional[LLMAdapters]:
    keys = [
        key
        for key in (
            settings.groq_api_key_1,
            settings.groq_api_key_2,
            settings.groq_api_key_3,
        )
        if key
    ]
    if not settings.groq_llm_enabled or not keys:
        return None

    if client is None:
        from ...redis_client import get_redis
        from ...services.llm.groq import GroqLLMClient
        from ...services.llm.keys import ApiKeyPool
        from ...services.llm.limiter import Budgets, InMemoryRateLimiter
        from ...services.llm.redis_limiter import FallbackRateLimiter, RedisRateLimiter

        budgets = Budgets(
            rpm=settings.groq_rpm_per_key,
            rpd=settings.groq_rpd_per_key,
            tpm=settings.groq_tpm_per_key,
            tpd=settings.groq_tpd_per_key,
        )
        if limiter is None:
            limiter = FallbackRateLimiter(
                RedisRateLimiter(get_redis(), budgets),
                InMemoryRateLimiter(budgets),
            )
        client = GroqLLMClient(
            ApiKeyPool(keys),
            limiter,
            model=settings.groq_model,
            base_url=settings.groq_base_url,
            request_timeout_seconds=settings.groq_request_timeout_seconds,
            max_wait_seconds=settings.groq_max_wait_seconds,
            reasoning_effort=settings.groq_reasoning_effort,
        )

    return LLMAdapters(
        GroqAnalyzer(client),
        GroqQuestionGenerator(client),
        GroqEvaluator(client),
    )
```

- [ ] **Step 5: Run the tests**

Run: `$env:REDIS_PORT='6380'; & "D:\python\project\StudentHub\venv\Scripts\python.exe" -m pytest backend/tests/llm/test_adapters.py -v`

Expected: 13 passed.

- [ ] **Step 6: Commit**

```powershell
git add -- backend/services/llm/prompts.py backend/interview_engine/adapters/llm.py backend/tests/llm/test_adapters.py
git commit -m "feat(interview-engine): add Groq analyzer, generator and evaluator adapters"
```

---

### Task 6: Engine analyzer guard and opt-in activation

**Files:**
- Modify: `backend/interview_engine/application/engine.py` (imports; around line 506)
- Modify: `backend/interview_engine/adapters/factory.py`
- Create: `backend/tests/interview_engine/test_engine_analyzer_guard.py`
- Modify: `pytest.ini`
- Modify: `backend/tests/llm/test_adapters.py` (add the two `build_llm_adapters` tests)

**Interfaces:**
- Consumes: `LLMAdapters`, `build_llm_adapters` (Task 5); `Analysis` from contracts.
- Produces: engine degrades instead of raising; `build_engine` selects real adapters when enabled.

- [ ] **Step 1: Add the `llm` pytest marker**

In `pytest.ini`, replace the `markers` line with:

```ini
markers =
    integration: requires a local MongoDB replica set
    llm: requires a live Groq API key and network access
```

- [ ] **Step 2: Write the failing guard test**

Create `backend/tests/interview_engine/test_engine_analyzer_guard.py`:

```python
import pytest

from backend.interview_engine.adapters.memory_store import InMemorySessionStore
from backend.interview_engine.adapters.scripted import (
    DeterministicEvaluator,
    ScriptedQuestionGenerator,
)
from backend.interview_engine.adapters.system import InMemoryLease, SystemClock, UuidIds
from backend.interview_engine.application.engine import InterviewEngine
from backend.interview_engine.contracts.messages import StartSessionCommand, SubmitTurnCommand


class RaisingAnalyzer:
    async def analyze(self, request):
        raise RuntimeError("provider exploded")


def _engine():
    store = InMemorySessionStore()
    engine = InterviewEngine(
        store=store,
        lease=InMemoryLease(),
        clock=SystemClock(),
        ids=UuidIds(),
        analyzer=RaisingAnalyzer(),
        generator=ScriptedQuestionGenerator(),
        evaluator=DeterministicEvaluator(),
    )
    return engine, store


async def _started(engine):
    return await engine.start(
        StartSessionCommand(
            candidate_id="c1",
            interview_type="behavioral",
            mode="practice",
            device_id="d1",
            client_request_id="req-guard",
            role="Senior Engineer",
            company="Acme",
        )
    )


async def test_submit_turn_survives_a_raising_analyzer():
    engine, store = _engine()
    started = await _started(engine)
    result = await engine.submit_turn(
        SubmitTurnCommand(
            candidate_id="c1",
            session_id=started.session_id,
            device_id="d1",
            fencing_token=started.fencing_token,
            turn_idempotency_key="turn-guard",
            kind="answer",
            text="I led the migration and cut errors by half.",
            question_id=started.question_id,
        )
    )
    assert result.session_id == started.session_id
    turns = await store.turns_for_session(started.session_id)
    assert len(turns) == 1
    evidence = await store.evidence_for_session(started.session_id)
    assert evidence == []


async def test_second_turn_still_works_after_a_degraded_analysis():
    engine, store = _engine()
    started = await _started(engine)
    first = await engine.submit_turn(
        SubmitTurnCommand(
            candidate_id="c1",
            session_id=started.session_id,
            device_id="d1",
            fencing_token=started.fencing_token,
            turn_idempotency_key="turn-a",
            kind="answer",
            text="I led the migration and cut errors by half.",
            question_id=started.question_id,
        )
    )
    second = await engine.submit_turn(
        SubmitTurnCommand(
            candidate_id="c1",
            session_id=started.session_id,
            device_id="d1",
            fencing_token=started.fencing_token,
            turn_idempotency_key="turn-b",
            kind="answer",
            text="I also mentored two engineers through the rollout.",
            question_id=first.question_id,
        )
    )
    assert second.session_id == started.session_id
    assert len(await store.turns_for_session(started.session_id)) == 2
```

- [ ] **Step 3: Run it to verify it fails**

Run: `$env:REDIS_PORT='6380'; & "D:\python\project\StudentHub\venv\Scripts\python.exe" -m pytest backend/tests/interview_engine/test_engine_analyzer_guard.py -v`

Expected: FAIL, `RuntimeError: provider exploded` propagates from `submit_turn`.

- [ ] **Step 4: Add the guard**

In `backend/interview_engine/application/engine.py`, add `import logging` after `import asyncio` (line 1), add `Analysis` to the `from ..contracts.records import (...)` list, and add after the imports:

```python
logger = logging.getLogger(__name__)

_ANALYSIS_UNAVAILABLE = "analysis_unavailable"
```

Then replace the analyzer call at line 506 with:

```python
        try:
            analysis = await self.analyzer.analyze(
                AnalysisRequest(
                    session_id=record.session_id,
                    turn_id=turn.turn_id,
                    question_id=turn.question_id,
                    slot_id=slot.slot_id,
                    competency=slot.competency,
                    text=cmd.text,
                )
            )
        except Exception:
            logger.warning("analyzer failed, degrading turn", exc_info=True)
            analysis = Analysis(
                signal="incomplete",
                instance="same",
                substantively_deficient=True,
                limitation=_ANALYSIS_UNAVAILABLE,
            )
```

- [ ] **Step 5: Run the guard and engine tests**

Run: `$env:REDIS_PORT='6380'; & "D:\python\project\StudentHub\venv\Scripts\python.exe" -m pytest backend/tests/interview_engine -q`

Expected: 181 passed (179 + 2 new).

- [ ] **Step 6: Write the failing activation tests**

Append to `backend/tests/llm/test_adapters.py`:

```python
class _Settings:
    groq_llm_enabled = False
    groq_api_key_1 = "gsk_a"
    groq_api_key_2 = None
    groq_api_key_3 = None
    groq_model = "openai/gpt-oss-120b"
    groq_base_url = "https://example.invalid"
    groq_rpm_per_key = 25
    groq_rpd_per_key = 900
    groq_tpm_per_key = 7000
    groq_tpd_per_key = 180000
    groq_max_wait_seconds = 60
    groq_request_timeout_seconds = 30
    groq_reasoning_effort = "low"


def _settings(**overrides):
    settings = _Settings()
    for name, value in overrides.items():
        setattr(settings, name, value)
    return settings


def test_build_llm_adapters_returns_none_when_disabled():
    from backend.interview_engine.adapters.llm import build_llm_adapters

    assert build_llm_adapters(_settings(groq_llm_enabled=False)) is None


def test_build_llm_adapters_returns_none_without_keys():
    from backend.interview_engine.adapters.llm import build_llm_adapters

    settings = _settings(groq_llm_enabled=True, groq_api_key_1=None)
    assert build_llm_adapters(settings) is None


def test_build_llm_adapters_wires_the_three_real_adapters():
    from backend.interview_engine.adapters.llm import (
        GroqAnalyzer,
        GroqEvaluator,
        GroqQuestionGenerator,
        build_llm_adapters,
    )

    built = build_llm_adapters(
        _settings(groq_llm_enabled=True), client=FakeLLM("unused")
    )
    assert isinstance(built.analyzer, GroqAnalyzer)
    assert isinstance(built.generator, GroqQuestionGenerator)
    assert isinstance(built.evaluator, GroqEvaluator)
```

Run: `$env:REDIS_PORT='6380'; & "D:\python\project\StudentHub\venv\Scripts\python.exe" -m pytest backend/tests/llm/test_adapters.py -v`

Expected: 3 failed (2 on missing wiring and one `AttributeError` for the dataclass without the fields) — the point is the file must fail before Step 7.

- [ ] **Step 7: Wire the factory**

Replace `backend/interview_engine/adapters/factory.py` with:

```python
from .llm import build_llm_adapters
from .redis_lease import RedisLease
from .scripted import (
    DeterministicEvaluator,
    HeuristicAnalyzer,
    ScriptedQuestionGenerator,
)
from .system import InMemoryLease, SystemClock, UuidIds


def build_engine(
    store=None,
    lease=None,
    redis_client=None,
    analyzer=None,
    generator=None,
    evaluator=None,
):
    from ..application.engine import InterviewEngine

    if store is None:
        from ...database import get_database
        from ...redis_client import get_redis

        from .mongo_store import MongoSessionStore

        database = get_database()
        redis_client = redis_client or get_redis()
        store = MongoSessionStore(database, database.client)
        lease = lease or RedisLease(redis_client)
    if lease is None:
        lease = InMemoryLease()

    if analyzer is None or generator is None or evaluator is None:
        from ...config import settings

        llm = build_llm_adapters(settings)
        if llm is not None:
            analyzer = analyzer or llm.analyzer
            generator = generator or llm.generator
            evaluator = evaluator or llm.evaluator

    return InterviewEngine(
        store=store,
        lease=lease,
        clock=SystemClock(),
        ids=UuidIds(),
        analyzer=analyzer or HeuristicAnalyzer(),
        generator=generator or ScriptedQuestionGenerator(),
        evaluator=evaluator or DeterministicEvaluator(),
    )
```

- [ ] **Step 8: Run the full engine and llm suites**

Run: `$env:REDIS_PORT='6380'; & "D:\python\project\StudentHub\venv\Scripts\python.exe" -m pytest backend/tests/llm backend/tests/interview_engine -q`

Expected: llm tests pass (3 new activation tests included) and 181 engine tests pass.

- [ ] **Step 9: Commit**

```powershell
git add -- pytest.ini backend/interview_engine/application/engine.py backend/interview_engine/adapters/factory.py backend/tests/interview_engine/test_engine_analyzer_guard.py backend/tests/llm/test_adapters.py
git commit -m "feat(interview-engine): guard analyzer calls and activate real LLM adapters"
```

---

### Task 7: Opt-in live interview test and full verification

**Files:**
- Create: `backend/tests/llm/test_live_interview.py`

**Interfaces:**
- Consumes: everything above, plus `InterviewEngine`, `InMemorySessionStore`, `InMemoryLease`, `SystemClock`, `UuidIds`, and the real adapters.
- Produces: nothing consumed later.

- [ ] **Step 1: Write the live test**

Create `backend/tests/llm/test_live_interview.py`:

```python
import os

import pytest

from backend.interview_engine.adapters.llm import (
    GroqAnalyzer,
    GroqEvaluator,
    GroqQuestionGenerator,
)
from backend.interview_engine.adapters.memory_store import InMemorySessionStore
from backend.interview_engine.adapters.system import InMemoryLease, SystemClock, UuidIds
from backend.interview_engine.application.engine import InterviewEngine
from backend.interview_engine.contracts.messages import (
    EndSessionCommand,
    RequestHintCommand,
    StartSessionCommand,
    SubmitTurnCommand,
)
from backend.services.llm.groq import GroqLLMClient
from backend.services.llm.keys import ApiKeyPool
from backend.services.llm.limiter import Budgets, InMemoryRateLimiter


def _keys():
    return [
        key
        for key in (
            os.environ.get("GROQ_API_KEY_1"),
            os.environ.get("GROQ_API_KEY_2"),
            os.environ.get("GROQ_API_KEY_3"),
        )
        if key
    ]


def _client():
    budgets = Budgets(rpm=25, rpd=900, tpm=7000, tpd=180000)
    return GroqLLMClient(
        ApiKeyPool(_keys()),
        InMemoryRateLimiter(budgets),
        model=os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b"),
        base_url=os.environ.get("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
        request_timeout_seconds=30,
        max_wait_seconds=60,
        reasoning_effort=os.environ.get("GROQ_REASONING_EFFORT", "low"),
        max_attempts=3,
    )


@pytest.mark.llm
@pytest.mark.integration
async def test_real_interview_completes_and_produces_a_report():
    keys = _keys()
    if not keys:
        pytest.skip("no GROQ_API_KEY_1/2/3 set")

    client = _client()
    store = InMemorySessionStore()
    engine = InterviewEngine(
        store=store,
        lease=InMemoryLease(),
        clock=SystemClock(),
        ids=UuidIds(),
        analyzer=GroqAnalyzer(client),
        generator=GroqQuestionGenerator(client),
        evaluator=GroqEvaluator(client),
    )

    started = await engine.start(
        StartSessionCommand(
            candidate_id="c-live",
            interview_type="behavioral",
            mode="practice",
            device_id="d-live",
            client_request_id="live-req-1",
            role="Backend Engineer",
            company="Acme",
        )
    )
    assert started.question_id

    answer = (
        "I owned the checkout migration. I split it into three phases, wrote the "
        "rollback plan, and cut error rates by half within six weeks."
    )
    result = await engine.submit_turn(
        SubmitTurnCommand(
            candidate_id="c-live",
            session_id=started.session_id,
            device_id="d-live",
            fencing_token=started.fencing_token,
            turn_idempotency_key="live-turn-1",
            kind="answer",
            text=answer,
            question_id=started.question_id,
        )
    )
    assert result.session_id == started.session_id

    hint = await engine.request_hint(
        RequestHintCommand(
            candidate_id="c-live",
            session_id=started.session_id,
            device_id="d-live",
            fencing_token=started.fencing_token,
            hint_idempotency_key="live-hint-1",
            question_id=started.question_id,
        )
    )
    assert hint.hint
    assert hint.remaining >= 0

    ended = await engine.end(
        EndSessionCommand(
            candidate_id="c-live",
            session_id=started.session_id,
            device_id="d-live",
            fencing_token=started.fencing_token,
            end_command_id="live-end-1",
        )
    )
    assert ended.session_id == started.session_id
    assert ended.status == "completed"

    await engine.drain_outbox(limit=10)
    report = await engine.get_report("c-live", ended.report_id)
    assert report is not None
    assert report.report_id == ended.report_id
```

`get_report` takes `(candidate_id, report_id)` and returns a `ReportRecord`. The end
command's id field is `end_command_id`, and `HintResult` exposes `hint`, not `text`.

- [ ] **Step 2: Run it without keys to confirm it skips**

Run: `$env:REDIS_PORT='6380'; & "D:\python\project\StudentHub\venv\Scripts\python.exe" -m pytest backend/tests/llm/test_live_interview.py -v`

Expected: 1 skipped, reason `no GROQ_API_KEY_1/2/3 set`.

- [ ] **Step 3: Run it with real keys**

Set keys in the shell for this run only (never write them to a file under version control):

```powershell
$env:GROQ_API_KEY_1='<key1>'; $env:GROQ_API_KEY_2='<key2>'; $env:GROQ_API_KEY_3='<key3>'; $env:REDIS_PORT='6380'
& "D:\python\project\StudentHub\venv\Scripts\python.exe" -m pytest backend/tests/llm/test_live_interview.py -v
```

Expected: 1 passed. If it fails with `daily_exhausted` or a 400 on a parameter, record the exact provider message in the task report before changing anything.

- [ ] **Step 4: Run the whole engine and llm suites**

Run: `$env:REDIS_PORT='6380'; & "D:\python\project\StudentHub\venv\Scripts\python.exe" -m pytest backend/tests/llm backend/tests/interview_engine -q`

Expected: all pass, the live test skipped unless keys are exported.

- [ ] **Step 5: Run the backend suite**

Run: `$env:REDIS_PORT='6380'; & "D:\python\project\StudentHub\venv\Scripts\python.exe" -m pytest backend/tests -q`

Expected: 275 passed (Task 12's route migration is not part of this plan and is still stashed; the baseline is 275).

- [ ] **Step 6: Commit**

```powershell
git add -- backend/tests/llm/test_live_interview.py
git commit -m "test(llm): add opt-in live interview test against Groq"
```

- [ ] **Step 7: Report**

Record in the task report: whether the live test passed against the real provider, the observed token usage if logged, and any parameter the provider rejected. Then hand back for the whole-branch review.

---

## Self-Review

**Spec coverage:**

- Configuration table → Task 1, Step 1.
- Rolling minute windows, 25-hour daily buckets, over-count property → Task 1 tests plus Task 2 Lua.
- Atomic reservation via Lua → Task 2.
- Settlement refund/overage/full refund → Task 1 (in-memory) and Task 2 (Lua).
- Bounded wait, no hang, daily vs minute distinction → Task 4 (`max_wait_seconds`, `daily_exhausted`).
- 429 with `retry-after`, rotation → Task 4.
- Redis-down degradation → Task 2 (`FallbackRateLimiter`).
- Key fingerprints, no raw key in logs/Redis → Task 3 tests and Task 4 log test.
- `max_completion_tokens`, `reasoning_effort`, `finish_reason == "length"` → Task 4.
- Three adapters, strict parsing, enum validation, evaluator rejects unknown competency and never scores → Task 5.
- Degradation ladder (empty question, degraded analysis, evaluator raises) → Task 5.
- Engine guard at the analyzer call → Task 6.
- `groq_llm_enabled` gating and factory activation → Task 6.
- `llm` marker and opt-in live test → Task 6 Step 1 and Task 7.
- Default suite passes with no key and no Redis → Task 7 Step 5.

**Placeholders:** none. Every code step carries the code.

**Type consistency:** `Reservation` is built positionally as `(keyhash, request_id, tokens, at_ms)` in tasks 1, 2 and 4; `ReserveResult` as `(reservation, wait_ms, reason)`; `ApiKey` is built by keyword in Task 3 with `value` excluded from `repr`. `LLMAdapters` exposes `.analyzer`, `.generator`, `.evaluator`, consumed by Task 6. Budget kwargs `rpm/rpd/tpm/tpd` are identical everywhere.

**Deliberate gaps:** usage metrics dashboards, streaming, and unification with `services/llm_service.py` are out of scope per the spec's Deferred Work. Task 12 of the engine plan (route compatibility) stays stashed and is unaffected by this plan.
