"""HTTP-based local LLM adapter (e.g. Ollama, LM Studio).

Phase 1 keeps this minimal: POST to a configured endpoint with `prompt` and
expect a JSON `{ "response": "..." }`. Override as needed for your runtime.
"""

from __future__ import annotations

from typing import Optional

import httpx

from app.llm.base_client import BaseLLMClient, LLMResponse
from app.utils.token_counter import estimate_cost


class LocalLLMClient(BaseLLMClient):
    name = "local"

    def __init__(self, endpoint: str = "http://localhost:11434/api/generate",
                 default_model: str = "llama3") -> None:
        self._endpoint = endpoint
        self._default_model = default_model

    def complete(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        max_tokens: int = 1200,
        temperature: float = 0.2,
    ) -> LLMResponse:
        model_name = model or self._default_model
        response = httpx.post(
            self._endpoint,
            json={
                "model": model_name,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": temperature, "num_predict": max_tokens},
            },
            timeout=120,
        )
        response.raise_for_status()
        data = response.json()
        text = data.get("response", "")
        cost = estimate_cost(model_name, prompt, text)
        return LLMResponse(
            text=text,
            model_name=model_name,
            input_tokens=cost.input_tokens,
            output_tokens=cost.output_tokens,
            estimated_cost=cost.estimated_cost,
        )
