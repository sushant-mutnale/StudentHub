from types import SimpleNamespace

import pytest

from backend.services.llm.groq import (
    GroqLLMClient,
    LLMUnavailable,
    estimate_tokens,
)
from backend.services.llm.keys import ApiKeyPool
from backend.services.llm.limiter import Budgets, InMemoryRateLimiter


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
    assert kwargs["temperature"] == 0.2
    assert "response_format" not in kwargs


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

    pool = ApiKeyPool(["gsk_a", "gsk_b"])
    first_key, second_key = list(pool)
    clock = FakeClock()
    limiter = InMemoryRateLimiter(
        Budgets(rpm=10, rpd=100, tpm=100000, tpd=1000000), clock=clock
    )
    served = []

    def factory(api_key):
        served.append(api_key.keyhash)
        if api_key.keyhash == first_key.keyhash:
            return FakeClient([rate_limited])
        return FakeClient([_response("second key")])

    client = GroqLLMClient(
        pool,
        limiter,
        model="openai/gpt-oss-120b",
        base_url="https://example.invalid/openai/v1",
        request_timeout_seconds=5,
        max_wait_seconds=60,
        client_factory=factory,
        clock=clock,
        sleep=NoSleep(clock),
    )
    completion = await client.complete(system="s", user="u", max_completion_tokens=10)
    assert completion.text == "second key"
    assert completion.keyhash == second_key.keyhash
    assert served == [first_key.keyhash, second_key.keyhash]
    blocked = await limiter.reserve(first_key.keyhash, 1)
    assert blocked.reservation is None
    assert blocked.reason == "blocked"


async def test_transport_error_refunds_the_reservation_and_fails():
    pool = ApiKeyPool(["gsk_a"])
    keyhash = list(pool)[0].keyhash
    clock = FakeClock()
    limiter = InMemoryRateLimiter(
        Budgets(rpm=10, rpd=100, tpm=20, tpd=10000), clock=clock
    )
    fake = FakeClient([RuntimeError("connection reset")])
    client = GroqLLMClient(
        pool,
        limiter,
        model="openai/gpt-oss-120b",
        base_url="https://example.invalid/openai/v1",
        request_timeout_seconds=5,
        max_wait_seconds=60,
        client_factory=lambda api_key: fake,
        clock=clock,
        sleep=NoSleep(clock),
    )
    with pytest.raises(LLMUnavailable) as caught:
        await client.complete(system="s", user="u", max_completion_tokens=10)
    assert caught.value.reason == "transport_error"
    result = await limiter.reserve(keyhash, 20)
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


async def test_complete_waits_for_the_minute_window_then_succeeds():
    clock = FakeClock()
    pool = ApiKeyPool(["gsk_a"])
    limiter = InMemoryRateLimiter(
        Budgets(rpm=1, rpd=100, tpm=100000, tpd=1000000), clock=clock
    )
    fake = FakeClient([_response("first"), _response("second")])
    client = GroqLLMClient(
        pool,
        limiter,
        model="openai/gpt-oss-120b",
        base_url="https://example.invalid/openai/v1",
        request_timeout_seconds=5,
        max_wait_seconds=120,
        client_factory=lambda api_key: fake,
        clock=clock,
        sleep=NoSleep(clock),
    )
    first = await client.complete(system="s", user="u", max_completion_tokens=10)
    assert first.text == "first"
    second = await client.complete(system="s", user="u", max_completion_tokens=10)
    assert second.text == "second"
    assert clock.now_ms == 1_060_000


class FrozenSleep:
    async def __call__(self, seconds: float) -> None:
        return None


async def test_wait_retries_are_bounded_when_the_clock_does_not_advance():
    clock = FakeClock()
    pool = ApiKeyPool(["gsk_a"])
    limiter = InMemoryRateLimiter(
        Budgets(rpm=0, rpd=100, tpm=100000, tpd=1000000), clock=clock
    )
    client = GroqLLMClient(
        pool,
        limiter,
        model="openai/gpt-oss-120b",
        base_url="https://example.invalid/openai/v1",
        request_timeout_seconds=5,
        max_wait_seconds=3600,
        client_factory=lambda api_key: FakeClient([]),
        clock=clock,
        sleep=FrozenSleep(),
    )
    with pytest.raises(LLMUnavailable) as caught:
        await client.complete(system="s", user="u", max_completion_tokens=10)
    assert caught.value.reason == "wait_budget_exceeded"


class RecordingLimiter:
    def __init__(self, inner):
        self._inner = inner
        self.blocks = []

    async def reserve(self, keyhash, tokens):
        return await self._inner.reserve(keyhash, tokens)

    async def settle(self, reservation, actual_tokens):
        return await self._inner.settle(reservation, actual_tokens)

    async def block(self, keyhash, seconds):
        self.blocks.append(seconds)
        return await self._inner.block(keyhash, seconds)


async def test_missing_retry_after_uses_bounded_exponential_backoff():
    first_429 = Exception("429")
    first_429.status_code = 429
    first_429.response = SimpleNamespace(headers={})
    second_429 = Exception("429")
    second_429.status_code = 429
    second_429.response = SimpleNamespace(headers={})

    pool = ApiKeyPool(["gsk_a", "gsk_b", "gsk_c"])
    clock = FakeClock()
    limiter = RecordingLimiter(
        InMemoryRateLimiter(
            Budgets(rpm=10, rpd=100, tpm=100000, tpd=1000000), clock=clock
        )
    )

    def factory(api_key):
        if api_key.keyhash == list(pool)[0].keyhash:
            return FakeClient([first_429])
        if api_key.keyhash == list(pool)[1].keyhash:
            return FakeClient([second_429])
        return FakeClient([_response("third key")])

    client = GroqLLMClient(
        pool,
        limiter,
        model="openai/gpt-oss-120b",
        base_url="https://example.invalid/openai/v1",
        request_timeout_seconds=5,
        max_wait_seconds=60,
        client_factory=factory,
        clock=clock,
        sleep=NoSleep(clock),
    )
    completion = await client.complete(system="s", user="u", max_completion_tokens=10)
    assert completion.text == "third key"
    assert limiter.blocks == [2.0, 4.0]


async def test_429_path_never_leaks_a_key_into_a_log(monkeypatch):
    rate_limited = Exception("429 rate limited")
    rate_limited.status_code = 429
    rate_limited.response = SimpleNamespace(headers={"retry-after": "30"})

    logged = []

    import backend.services.llm.groq as groq_module

    class RecordingLogger:
        def info(self, message, *args, **kwargs):
            logged.append(str(message) + str(args) + str(kwargs))

        def warning(self, message, *args, **kwargs):
            logged.append(str(message) + str(args) + str(kwargs))

        def exception(self, message, *args, **kwargs):
            logged.append(str(message) + str(args) + str(kwargs))

    monkeypatch.setattr(groq_module, "logger", RecordingLogger())

    pool = ApiKeyPool(["gsk_secret_one", "gsk_secret_two"])
    first_key = list(pool)[0]
    clock = FakeClock()
    limiter = InMemoryRateLimiter(
        Budgets(rpm=10, rpd=100, tpm=100000, tpd=1000000), clock=clock
    )

    def factory(api_key):
        if api_key.keyhash == first_key.keyhash:
            return FakeClient([rate_limited])
        return FakeClient([_response("ok")])

    client = GroqLLMClient(
        pool,
        limiter,
        model="openai/gpt-oss-120b",
        base_url="https://example.invalid/openai/v1",
        request_timeout_seconds=5,
        max_wait_seconds=60,
        client_factory=factory,
        clock=clock,
        sleep=NoSleep(clock),
    )
    await client.complete(system="s", user="u", max_completion_tokens=10)
    assert logged
    assert all("gsk_secret_one" not in entry for entry in logged)
    assert all("gsk_secret_two" not in entry for entry in logged)


class ScriptedLimiter:
    def __init__(self, results):
        self._results = list(results)
        self.blocks = []

    async def reserve(self, keyhash, tokens):
        for index, (wanted, result) in enumerate(self._results):
            if wanted == keyhash:
                self._results.pop(index)
                return result
        raise AssertionError(f"unexpected reserve for {keyhash}")

    async def settle(self, reservation, actual_tokens):
        return None

    async def block(self, keyhash, seconds):
        self.blocks.append(seconds)


async def test_daily_failure_on_one_key_does_not_mask_a_shorter_minute_wait():
    from backend.services.llm.limiter import Reservation, ReserveResult

    pool = ApiKeyPool(["gsk_a", "gsk_b"])
    daily_key, minute_key = list(pool)
    limiter = ScriptedLimiter(
        [
            (
                daily_key.keyhash,
                ReserveResult(None, 5_000, "daily"),
            ),
            (
                minute_key.keyhash,
                ReserveResult(None, 40_000, "minute_requests"),
            ),
            (
                daily_key.keyhash,
                ReserveResult(None, 5_000, "daily"),
            ),
            (
                minute_key.keyhash,
                ReserveResult(
                    Reservation(minute_key.keyhash, "rid-1", 13, 1_000_000), 0, "ok"
                ),
            ),
        ]
    )
    fake = FakeClient([_response("after the wait")])
    clock = FakeClock()
    client = GroqLLMClient(
        pool,
        limiter,
        model="openai/gpt-oss-120b",
        base_url="https://example.invalid/openai/v1",
        request_timeout_seconds=5,
        max_wait_seconds=60,
        client_factory=lambda api_key: fake,
        clock=clock,
        sleep=NoSleep(clock),
    )
    completion = await client.complete(system="s", user="u", max_completion_tokens=10)
    assert completion.text == "after the wait"
    assert completion.keyhash == minute_key.keyhash
    assert clock.now_ms == 1_040_000
