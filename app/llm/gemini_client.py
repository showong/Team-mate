"""Google Gemini adapter (lazy import)."""

from __future__ import annotations

from typing import Optional

from app.llm.base_client import BaseLLMClient, LLMResponse
from app.utils.token_counter import estimate_cost


class GeminiClient(BaseLLMClient):
    name = "gemini"

    def __init__(self, api_key: str, default_model: str = "gemini-1.5-flash") -> None:
        try:
            import google.generativeai as genai  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "google-generativeai is not installed. "
                "`pip install google-generativeai` or use LLM_PROVIDER=mock."
            ) from exc

        genai.configure(api_key=api_key)
        self._genai = genai
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
        m = self._genai.GenerativeModel(model_name)
        response = m.generate_content(
            prompt,
            generation_config={"max_output_tokens": max_tokens, "temperature": temperature},
        )
        text = getattr(response, "text", "")
        cost = estimate_cost(model_name, prompt, text)
        return LLMResponse(
            text=text,
            model_name=model_name,
            input_tokens=cost.input_tokens,
            output_tokens=cost.output_tokens,
            estimated_cost=cost.estimated_cost,
        )
