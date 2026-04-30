"""Multi-provider router LLM client.

각 agent가 `complete(prompt, model="claude-opus-4-7")` 처럼 모델명을 지정하면,
모델명 prefix를 보고 해당 provider의 client로 dispatch한다.

API key가 없는 provider 호출은 mock client로 fallback (테스트 모드).
"""

from __future__ import annotations

from typing import Dict, Optional

from app.llm.base_client import BaseLLMClient, LLMResponse
from app.llm.mock_client import MockLLMClient


class MultiProviderLLMClient(BaseLLMClient):
    name = "multi"

    PREFIX_MAP = {
        "openai":    ("gpt-", "o1-", "o3-"),
        "anthropic": ("claude-",),
        "gemini":    ("gemini-",),
    }

    def __init__(
        self,
        *,
        openai_api_key: Optional[str] = None,
        anthropic_api_key: Optional[str] = None,
        gemini_api_key: Optional[str] = None,
        fallback_to_mock: bool = True,
    ) -> None:
        self._clients: Dict[str, BaseLLMClient] = {}
        self._fallback_to_mock = fallback_to_mock

        if openai_api_key:
            try:
                from app.llm.openai_client import OpenAIClient
                self._clients["openai"] = OpenAIClient(openai_api_key)
            except Exception:
                pass

        if anthropic_api_key:
            try:
                from app.llm.anthropic_client import AnthropicClient
                self._clients["anthropic"] = AnthropicClient(anthropic_api_key)
            except Exception:
                pass

        if gemini_api_key:
            try:
                from app.llm.gemini_client import GeminiClient
                self._clients["gemini"] = GeminiClient(gemini_api_key)
            except Exception:
                pass

        if fallback_to_mock:
            self._clients["mock"] = MockLLMClient()

    def complete(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        max_tokens: int = 1200,
        temperature: float = 0.2,
    ) -> LLMResponse:
        provider = self._infer_provider(model)
        client = self._clients.get(provider)

        # Provider 키가 없으면 mock으로 폴백
        if client is None:
            if self._fallback_to_mock and "mock" in self._clients:
                client = self._clients["mock"]
            else:
                raise RuntimeError(
                    f"Provider '{provider}' (model='{model}') 호출 실패: API key 미설정."
                )

        return client.complete(
            prompt, model=model, max_tokens=max_tokens, temperature=temperature
        )

    @classmethod
    def _infer_provider(cls, model: Optional[str]) -> str:
        if not model:
            return "mock"
        for provider, prefixes in cls.PREFIX_MAP.items():
            if any(model.startswith(p) for p in prefixes):
                return provider
        return "mock"

    def available_providers(self) -> list[str]:
        return [p for p in self._clients.keys() if p != "mock"]
