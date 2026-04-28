"""Factory that resolves LLM_PROVIDER → concrete client."""

from __future__ import annotations

from typing import Optional

from app.config import Settings, get_settings
from app.llm.base_client import BaseLLMClient
from app.llm.mock_client import MockLLMClient


def build_llm_client(settings: Optional[Settings] = None) -> BaseLLMClient:
    settings = settings or get_settings()
    provider = settings.llm_provider.lower()

    if provider == "mock":
        return MockLLMClient()

    if provider == "openai":
        from app.llm.openai_client import OpenAIClient

        if not settings.openai_api_key:
            raise RuntimeError("LLM_PROVIDER=openai but OPENAI_API_KEY is empty.")
        return OpenAIClient(api_key=settings.openai_api_key)

    if provider == "anthropic":
        from app.llm.anthropic_client import AnthropicClient

        if not settings.anthropic_api_key:
            raise RuntimeError("LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY is empty.")
        return AnthropicClient(api_key=settings.anthropic_api_key)

    if provider == "gemini":
        from app.llm.gemini_client import GeminiClient

        if not settings.gemini_api_key:
            raise RuntimeError("LLM_PROVIDER=gemini but GEMINI_API_KEY is empty.")
        return GeminiClient(api_key=settings.gemini_api_key)

    if provider == "local":
        from app.llm.local_client import LocalLLMClient

        return LocalLLMClient()

    raise ValueError(f"Unknown LLM_PROVIDER: {provider}")
