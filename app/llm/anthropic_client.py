"""Anthropic Messages API adapter (lazy import)."""

from __future__ import annotations

from typing import Optional

from app.llm.base_client import BaseLLMClient, LLMResponse
from app.utils.token_counter import estimate_cost


class AnthropicClient(BaseLLMClient):
    name = "anthropic"

    def __init__(self, api_key: str, default_model: str = "claude-sonnet-4-6") -> None:
        try:
            import anthropic  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "anthropic SDK is not installed. `pip install anthropic` or use LLM_PROVIDER=mock."
            ) from exc

        self._client = anthropic.Anthropic(api_key=api_key)
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
        message = self._client.messages.create(
            model=model_name,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        # message.content is a list of content blocks
        text = "".join(getattr(block, "text", "") for block in message.content)
        usage = getattr(message, "usage", None)
        if usage is not None:
            in_tok = getattr(usage, "input_tokens", 0)
            out_tok = getattr(usage, "output_tokens", 0)
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
