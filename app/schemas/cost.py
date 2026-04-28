"""Cost log entry per LLM call."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CostLog(BaseModel):
    cost_id: str
    project_id: str
    step: str  # e.g. "junior_research", "deputy_review"
    model_name: str
    input_tokens: int
    output_tokens: int
    estimated_cost: float
    created_at: datetime = Field(default_factory=datetime.utcnow)
