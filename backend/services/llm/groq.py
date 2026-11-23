import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Awaitable, Callable, Dict, Optional

from .keys import ApiKey, ApiKeyPool
from .limiter import RateLimiter

logger = logging.getLogger(__name__)

_MAX_ATTEMPTS = 6
_RETRY_BACKOFF_BASE = 2.0
_RETRY_BACKOFF_CAP = 8.0


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


def _retry_after_seconds(exc: Exception, attempt: int = 1) -> Optional[float]:
    if getattr(exc, "status_code", None) != 429:
        return None
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None) or {}
    raw = headers.get("retry-after") or headers.get("Retry-After")
    if raw is not None:
        try:
            return max(0.0, float(raw))
        except (TypeError, ValueError):
            pass
    backoff = _RETRY_BACKOFF_BASE * (2 ** max(0, attempt - 1))
    return min(_RETRY_BACKOFF_CAP, backoff)


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
        sleep: Optional[Callable[[float], Awaitable[None]]] = None,
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
        self._clients: Dict[str, object] = {}

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
        waits_left = self._max_attempts * 2

        while attempts_left > 0:
            key, reservation, wait_ms, reason = await self._reserve_any(reserved)
            if reservation is None:
                if reason == "daily":
                    raise LLMUnavailable("daily_exhausted")
                if wait_ms <= 0 or self._clock() + wait_ms > deadline_ms:
                    raise LLMUnavailable("wait_budget_exceeded")
                waits_left -= 1
                if waits_left <= 0:
                    raise LLMUnavailable("wait_budget_exceeded")
                logger.info(
                    "LLM rate limit reached, waiting %sms (%s)", wait_ms, reason
                )
                await self._sleep(wait_ms / 1000)
                continue

            attempts_left -= 1
            attempt_index = self._max_attempts - attempts_left
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
                retry_after = _retry_after_seconds(exc, attempt_index)
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
        daily_wait = None
        for key in self._pool:
            result = await self._limiter.reserve(key.keyhash, tokens)
            if result.reservation is not None:
                return key, result.reservation, 0, "ok"
            if result.reason == "daily":
                if daily_wait is None or result.wait_ms < daily_wait:
                    daily_wait = result.wait_ms
                continue
            if best_wait is None or result.wait_ms < best_wait:
                best_wait = result.wait_ms
                best_reason = result.reason
        if best_wait is not None:
            return None, None, best_wait, best_reason
        if daily_wait is not None:
            return None, None, daily_wait, "daily"
        return None, None, 0, best_reason

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
