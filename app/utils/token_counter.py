"""Approximate token counter and cost estimator.

Phase 1 keeps this dependency-free. We use a heuristic of ~4 chars per token
for English-heavy text and ~2 chars per token for CJK-heavy text. The exact
number is not critical here — what matters is consistent attribution per call
so cost trends are detectable.
"""

from __future__ import annotations

from dataclasses import dataclass


def count_tokens(text: str) -> int:
    if not text:
        return 0
    cjk = sum(1 for ch in text if "　" <= ch <= "鿿" or "가" <= ch <= "힯")
    other = len(text) - cjk
    # CJK ~2 chars/token, others ~4 chars/token
    return max(1, (cjk // 2) + (other // 4))


# Per-1k-token price table in arbitrary "credits". Phase 1 uses these as
# relative units so we can compare cost modes without binding to a real
# pricing sheet. Real pricing should be wired through the LLM client itself.
DEFAULT_PRICES = {
    "mock": (0.0, 0.0),
    "low_cost": (0.05, 0.15),
    "mid": (0.50, 1.50),
    "high": (3.00, 15.00),
    # OpenAI examples
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    # Anthropic examples
    "claude-haiku-4-5-20251001": (0.25, 1.25),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-opus-4-7": (15.00, 75.00),
    # Google Gemini examples
    "gemini-1.5-flash": (0.075, 0.30),
    "gemini-1.5-pro":   (1.25, 5.00),
    "gemini-2.0-flash": (0.10, 0.40),
}


@dataclass
class CostBreakdown:
    input_tokens: int
    output_tokens: int
    estimated_cost: float


def estimate_cost(model_name: str, input_text: str, output_text: str) -> CostBreakdown:
    in_tok = count_tokens(input_text)
    out_tok = count_tokens(output_text)
    in_price, out_price = DEFAULT_PRICES.get(model_name, DEFAULT_PRICES["mid"])
    cost = (in_tok / 1000.0) * in_price + (out_tok / 1000.0) * out_price
    return CostBreakdown(input_tokens=in_tok, output_tokens=out_tok, estimated_cost=round(cost, 4))
