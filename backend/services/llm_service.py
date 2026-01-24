"""
Flexible LLM Provider Configuration
Supports: OpenRouter, OpenAI, Gemini, Groq, Ollama (local)
Uses LangChain for provider-agnostic interface.
"""

import os
from typing import Optional, Literal
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

# Load environment variables
load_dotenv()

# Supported providers
LLMProvider = Literal["openrouter", "openai", "groq", "ollama"]


class LLMConfig:
    """
    Configuration for LLM providers.
    Environment variables:
    - OPENROUTER_API_KEY: For OpenRouter
    - OPENAI_API_KEY: For OpenAI
    - GROQ_API_KEY: For Groq
    - LLM_PROVIDER: Default provider (openrouter, openai, groq, ollama)
    - LLM_MODEL: Default model name
    """
    
    # Provider configurations
    PROVIDERS = {
        "openrouter": {
            "api_base": "https://openrouter.ai/api/v1",
            "env_key": "OPENROUTER_API_KEY",
            "default_model": "deepseek/deepseek-r1-0528:free"
        },
        "openai": {
            "api_base": "https://api.openai.com/v1",
            "env_key": "OPENAI_API_KEY",
            "default_model": "gpt-3.5-turbo"
        },
        "groq": {
            "api_base": "https://api.groq.com/openai/v1",
            "env_key": "GROQ_API_KEY",
            "default_model": "llama-3.1-70b-versatile"
        },
        "ollama": {
            "api_base": "http://localhost:11434/v1",
            "env_key": None,  # No API key needed for local
            "default_model": "llama3.2"
        }
    }
    
    @classmethod
    def get_default_provider(cls) -> str:
        return os.getenv("LLM_PROVIDER", "openrouter")
    
    @classmethod
    def get_api_key(cls, provider: str) -> Optional[str]:
        config = cls.PROVIDERS.get(provider, {})
        env_key = config.get("env_key")
        if env_key:
            return os.getenv(env_key)
        return "not-needed"  # For local providers like Ollama
    
    @classmethod
    def get_api_base(cls, provider: str) -> str:
        return cls.PROVIDERS.get(provider, {}).get("api_base", "")
    
    @classmethod
    def get_default_model(cls, provider: str) -> str:
        custom_model = os.getenv("LLM_MODEL")
        if custom_model:
            return custom_model
        return cls.PROVIDERS.get(provider, {}).get("default_model", "gpt-3.5-turbo")


class LLMService:
    """
    Provider-agnostic LLM service using LangChain.
    Supports switching providers at runtime.
    """
    
    def __init__(
        self, 
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ):
        self.provider = provider or LLMConfig.get_default_provider()
        self.model = model or LLMConfig.get_default_model(self.provider)
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._llm = None
    
    def _get_llm(self) -> ChatOpenAI:
        """Get or create the LLM instance."""
        if self._llm is None:
            api_key = LLMConfig.get_api_key(self.provider)
            api_base = LLMConfig.get_api_base(self.provider)
            
            if not api_key and self.provider != "ollama":
                raise ValueError(
                    f"API key not found for provider '{self.provider}'. "
                    f"Please set {LLMConfig.PROVIDERS[self.provider]['env_key']} in your .env file."
                )
            
            self._llm = ChatOpenAI(
                model=self.model,
                openai_api_key=api_key,
                openai_api_base=api_base,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
        
        return self._llm
    
    async def generate(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Generate a response from the LLM.
        
        Args:
            prompt: User prompt/question
            system_prompt: Optional system prompt for context
            
        Returns:
            Generated text response
        """
        llm = self._get_llm()
        
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))
        
        try:
            response = await llm.ainvoke(messages)
            return response.content
        except Exception as e:
            # Fallback to non-async if async fails
            try:
                response = llm.invoke(messages)
                return response.content
            except Exception as inner_e:
                return f"Error generating response: {str(inner_e)}"
    
    def generate_sync(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Synchronous version of generate.
        """
        llm = self._get_llm()
        
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))
        
        try:
            response = llm.invoke(messages)
            return response.content
        except Exception as e:
            return f"Error generating response: {str(e)}"
    
    def switch_provider(
        self, 
        provider: str, 
        model: Optional[str] = None
    ):
        """Switch to a different LLM provider."""
        if provider not in LLMConfig.PROVIDERS:
            raise ValueError(f"Unknown provider: {provider}. Supported: {list(LLMConfig.PROVIDERS.keys())}")
        
        self.provider = provider
        self.model = model or LLMConfig.get_default_model(provider)
        self._llm = None  # Reset to recreate with new provider


# Singleton instance for easy import
llm_service = LLMService()


# Convenience function for quick generation
async def generate_ai_response(
    prompt: str,
    system_prompt: Optional[str] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None
) -> str:
    """
    Quick helper to generate AI response.
    Creates a new LLMService if provider/model differs from default.
    """
    if provider or model:
        service = LLMService(provider=provider, model=model)
    else:
        service = llm_service
    
    return await service.generate(prompt, system_prompt)
