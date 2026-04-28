"""Sub-leader review and decision."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class Decision(str, Enum):
    APPROVED = "APPROVED"
    CONDITIONAL_APPROVED = "CONDITIONAL_APPROVED"
    REJECTED = "REJECTED"


class RetryTargetRole(str, Enum):
    JUNIOR = "junior"
    DEPUTY = "deputy"


class RetryTarget(BaseModel):
    role: RetryTargetRole
    assignee: Optional[str] = None  # e.g. junior_a
    reason: str


class ReviewScores(BaseModel):
    """1~5 점수. 부팀장이 평가."""

    accuracy: int = Field(ge=1, le=5)
    source_quality: int = Field(ge=1, le=5)
    logic: int = Field(ge=1, le=5)
    completeness: int = Field(ge=1, le=5)
    hallucination_risk: int = Field(ge=1, le=5)  # higher = safer

    @property
    def average(self) -> float:
        return (
            self.accuracy
            + self.source_quality
            + self.logic
            + self.completeness
            + self.hallucination_risk
        ) / 5.0


class Review(BaseModel):
    review_id: str
    project_id: str
    reviewer_role: str = "subleader"
    scores: ReviewScores
    decision: Decision
    feedback: str
    retry_targets: List[RetryTarget] = Field(default_factory=list)
    rejection_reason_code: Optional[str] = None  # used for circuit-breaker repetition check
    created_at: datetime = Field(default_factory=datetime.utcnow)
