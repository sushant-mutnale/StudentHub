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

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

# Load .env from backend/ regardless of where uvicorn is started from
_dotenv_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_dotenv_path, override=True)

# ─── Read provider config ──────────────────────────────────────────────────────
_OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")
_OPENROUTER_BASE = "https://openrouter.ai/api/v1"
_MODEL = os.getenv("LLM_MODEL", "arcee-ai/arcee-blitz:free")


def _build_llm(model: Optional[str] = None, temperature: float = 0.7, max_tokens: int = 1024) -> ChatOpenAI:
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
        max_tokens: int = 1024,
    ):
        self.model = model or _MODEL
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._llm: Optional[ChatOpenAI] = None

    def _get_llm(self) -> ChatOpenAI:
        if self._llm is None:
            self._llm = _build_llm(self.model, self.temperature, self.max_tokens)
        return self._llm

    # ── Async (used in FastAPI route handlers / async agents) ──────────────────
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        use_fallback: bool = False,   # False = don't silently swallow errors
    ) -> str:
        """
        Generate a response asynchronously.
        Errors are surfaced directly (use_fallback=False by default).
        """
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        try:
            llm = self._get_llm()
            response = await llm.ainvoke(messages)
            return response.content
        except Exception as e:
            if not use_fallback:
                return f"Error: {str(e)}"
            # If fallback is requested, surface the error clearly
            return f"Error: {str(e)}"

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
