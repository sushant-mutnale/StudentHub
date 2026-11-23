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

    pool = ApiKeyPool(["gsk_a", "gsk_b"])
    first_hash = list(pool)[0].keyhash
    clock = FakeClock()
    limiter = InMemoryRateLimiter(
        Budgets(rpm=10, rpd=100, tpm=100000, tpd=1000000), clock=clock
    )
    fake = FakeClient([rate_limited, _response("second key")])
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
    assert completion.text == "second key"
    assert len(fake.chat.completions.calls) == 2
    blocked = await limiter.reserve(first_hash, 1)
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
