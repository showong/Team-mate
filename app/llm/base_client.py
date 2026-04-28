"""LLM client interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class LLMResponse:
    text: str
    model_name: str
    input_tokens: int
    output_tokens: int
    estimated_cost: float


class BaseLLMClient(ABC):
    """Common surface every provider must implement.

    The orchestrator only ever talks to this interface, so swapping providers
    (or pinning one role to a different model) does not require changes in
    business logic.
    """

    name: str = "base"

    @abstractmethod
    def complete(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        max_tokens: int = 1200,
        temperature: float = 0.2,
    ) -> LLMResponse:
        """Run a single completion. Must return token counts for cost tracking."""
        raise NotImplementedError
