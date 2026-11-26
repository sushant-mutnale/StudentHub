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


async def test_settle_lowers_the_daily_token_bucket_to_actual_usage():
    limiter, clock = _limiter(rpd=1000, tpm=1000, tpd=1000)
    first = await limiter.reserve("kh", 700)
    await limiter.settle(first.reservation, actual_tokens=400)
    clock.advance(61_000)
    allowed = await limiter.reserve("kh", 500)
    assert allowed.reservation is not None


async def test_daily_buckets_over_count_for_a_full_day_and_release_after():
    limiter, clock = _limiter(rpm=100, rpd=2, tpm=100000, tpd=100000)
    clock.now_ms = 0
    await limiter.reserve("kh", 10)
    await limiter.reserve("kh", 10)
    clock.advance(24 * 3_600_000)
    still = await limiter.reserve("kh", 10)
    assert still.reservation is None
    assert still.reason == "daily"
    clock.advance(3_600_000)
    freed = await limiter.reserve("kh", 10)
    assert freed.reservation is not None


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
