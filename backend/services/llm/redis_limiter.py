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
