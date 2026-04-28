"""OpenAI Chat Completions adapter (lazy import)."""

from __future__ import annotations

from typing import Optional

from app.llm.base_client import BaseLLMClient, LLMResponse
from app.utils.token_counter import estimate_cost


class OpenAIClient(BaseLLMClient):
    name = "openai"

    def __init__(self, api_key: str, default_model: str = "gpt-4o-mini") -> None:
        try:
            from openai import OpenAI  # type: ignore
        except ImportError as exc:  # pragma: no cover - exercised only when SDK present
            raise RuntimeError(
                "openai SDK is not installed. `pip install openai` or use LLM_PROVIDER=mock."
            ) from exc

        self._client = OpenAI(api_key=api_key)
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
        response = self._client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        text = response.choices[0].message.content or ""
        usage = getattr(response, "usage", None)
        if usage is not None:
            in_tok = getattr(usage, "prompt_tokens", 0)
            out_tok = getattr(usage, "completion_tokens", 0)
            cost = estimate_cost(model_name, "" * in_tok, "" * out_tok)
            cost.input_tokens = in_tok
            cost.output_tokens = out_tok
        else:
            cost = estimate_cost(model_name, prompt, text)
        return LLMResponse(
            text=text,
            model_name=model_name,
            input_tokens=cost.input_tokens,
            output_tokens=cost.output_tokens,
            estimated_cost=cost.estimated_cost,
        )
