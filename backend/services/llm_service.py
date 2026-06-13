"""
Flexible LLM Provider Configuration — using OpenRouter via LangChain ChatOpenAI.
This follows the exact same pattern that is confirmed to work:

    llm = ChatOpenAI(
        model="arcee-ai/trinity-large-preview:free",
        openai_api_key=OPENROUTER_API_KEY,
        openai_api_base="https://openrouter.ai/api/v1",
    )
    response = llm.invoke([HumanMessage(content="...")])
    print(response.content)
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, retry_if_exception

logger = logging.getLogger(__name__)

# ─── Read provider config ──────────────────────────────────────────────────────
_OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")
_OPENROUTER_BASE = "https://openrouter.ai/api/v1"
_MODEL = os.getenv("LLM_MODEL", "arcee-ai/arcee-blitz:free")


def _is_retryable_exception(exception: Exception) -> bool:
    """Check if exception is a transient LLM error that should be retried."""
    if isinstance(exception, asyncio.TimeoutError):
        return True
    error_str = str(exception)
    return '429' in error_str or '503' in error_str or '502' in error_str


def _build_llm(model: Optional[str] = None, temperature: float = 0.7, max_tokens: int = 4096) -> ChatOpenAI:
    """Build a ChatOpenAI instance pointed at OpenRouter — same pattern as user's working script."""
    if not _OPENROUTER_KEY:
        raise ValueError("OPENROUTER_API_KEY not set in backend/.env")
    return ChatOpenAI(
        model=model or _MODEL,
        openai_api_key=_OPENROUTER_KEY,
        openai_api_base=_OPENROUTER_BASE,
        temperature=temperature,
        max_tokens=max_tokens,
    )


class LLMService:
    """
    Provider-agnostic LLM service backed by OpenRouter.
    Supports both sync (generate_sync) and async (generate) invocation.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ):
        self.model = model or _MODEL
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._llm: Optional[ChatOpenAI] = None

    def _get_llm(self) -> ChatOpenAI:
        if self._llm is None:
            self._llm = _build_llm(self.model, self.temperature, self.max_tokens)
        return self._llm

    @retry(
        retry=retry_if_exception(_is_retryable_exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True
    )
    async def _invoke_with_retry(self, messages: list) -> str:
        """Inner method with retry logic."""
        try:
            llm = self._get_llm()
            response = await asyncio.wait_for(
                llm.ainvoke(messages),
                timeout=30.0
            )
            return response.content
        except asyncio.TimeoutError:
            logger.warning("LLM request timed out")
            raise
        except Exception as e:
            logger.warning(f"LLM API error: {e}")
            raise

    # ── Async (used in FastAPI route handlers / async agents) ──────────────────
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        use_fallback: bool = False,   # False = don't silently swallow errors
    ) -> Optional[str]:
        """
        Generate a response asynchronously.
        Raises exceptions directly if use_fallback is False.
        If use_fallback is True, logs the error and returns None.
        """
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        try:
            return await self._invoke_with_retry(messages)
        except Exception as e:
            if use_fallback:
                logger.error(f"LLM service generate failed, using fallback: {e}")
                return None
            raise

    async def generate_from_messages(
        self,
        messages: list,
        use_fallback: bool = False
    ) -> Optional[str]:
        """
        Generate a response asynchronously from a list of structured LangChain messages.
        Raises exceptions directly if use_fallback is False.
        If use_fallback is True, logs the error and returns None.
        """
        try:
            return await self._invoke_with_retry(messages)
        except Exception as e:
            if use_fallback:
                logger.error(f"LLM service generate_from_messages failed, using fallback: {e}")
                return None
            raise

    # ── Sync (used in scripts / background tasks) ─────────────────────────────
    def generate_sync(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Generate a response synchronously — exactly the pattern user confirmed works:
            response = llm.invoke([HumanMessage(content=prompt)])
            return response.content
        """
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        try:
            llm = self._get_llm()
            response = llm.invoke(messages)   # ← exact same as user's working script
            return response.content
        except Exception as e:
            return f"Error generating response: {str(e)}"

    def switch_model(self, model: str):
        """Switch to a different model at runtime."""
        self.model = model
        self._llm = None  # reset so next call rebuilds


# ─── Module-level singleton ────────────────────────────────────────────────────
llm_service = LLMService()


# ─── Convenience function ──────────────────────────────────────────────────────
async def generate_ai_response(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: Optional[str] = None,
) -> str:
    """
    Quick helper. Creates a one-off LLMService if a specific model is requested,
    otherwise uses the module-level singleton.
    """
    if model:
        svc = LLMService(model=model)
    else:
        svc = llm_service
    return await svc.generate(prompt, system_prompt)


# ─── Backward-compat shims (keep old callers working) ────────────────────────
class LLMConfig:
    """Kept for backwards compatibility only."""
    PROVIDERS = {
        "openrouter": {
            "api_base": _OPENROUTER_BASE,
            "env_key": "OPENROUTER_API_KEY",
            "default_model": "arcee-ai/arcee-blitz:free",
        }
    }
    FALLBACK_CHAIN = ["openrouter"]

    @classmethod
    def get_default_provider(cls) -> str:
        return "openrouter"

    @classmethod
    def get_api_key(cls, provider: str = "openrouter") -> str:
        return _OPENROUTER_KEY

    @classmethod
    def get_api_base(cls, provider: str = "openrouter") -> str:
        return _OPENROUTER_BASE

    @classmethod
    def get_default_model(cls, provider: str = "openrouter", is_fallback: bool = False) -> str:
        return _MODEL
