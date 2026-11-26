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
        until = self._clock() + max(1, int(seconds * 1000))
        self._blocked_until[keyhash] = max(self._blocked_until.get(keyhash, 0), until)

    def _purge(self, keyhash: str, now: int) -> None:
        cutoff = now - _MINUTE_MS
        requests = self._requests.get(keyhash)
        if requests is not None:
            self._requests[keyhash] = [
                entry for entry in requests if entry[0] > cutoff
            ]
        tokens = self._tokens.get(keyhash)
        if tokens is not None:
            self._tokens[keyhash] = [
                entry for entry in tokens if entry[0] > cutoff
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
