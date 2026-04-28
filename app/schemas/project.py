"""Project-level schema."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ProjectStatus(str, Enum):
    CREATED = "CREATED"
    ROUTING = "ROUTING"
    TASK_SPLITTING = "TASK_SPLITTING"
    COLLECTING_SOURCES = "COLLECTING_SOURCES"
    RESEARCHING = "RESEARCHING"
    SUMMARIZING = "SUMMARIZING"
    REVIEWING = "REVIEWING"
    QUALITY_CHECKING = "QUALITY_CHECKING"
    RETRYING = "RETRYING"
    FINALIZING = "FINALIZING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    USER_INTERVENTION_REQUIRED = "USER_INTERVENTION_REQUIRED"


class CostMode(str, Enum):
    LOW_COST = "low_cost"
    BALANCED = "balanced"
    HIGH_QUALITY = "high_quality"
    TEST = "test"


class VerificationLevel(str, Enum):
    LIGHT = "light"
    STANDARD = "standard"
    STRICT = "strict"


class OutputLength(str, Enum):
    SHORT = "short"
    NORMAL = "normal"
    LONG = "long"


class ProjectCreate(BaseModel):
    """Inbound payload for `POST /projects`."""

    agenda: str = Field(..., min_length=1)
    purpose: Optional[str] = None
    conditions: Optional[str] = None
    cost_mode: CostMode = CostMode.BALANCED
    verification_level: VerificationLevel = VerificationLevel.STANDARD
    output_length: OutputLength = OutputLength.NORMAL


class Project(BaseModel):
    """Persistent project model used inside the orchestrator."""

    project_id: str
    agenda: str
    purpose: Optional[str] = None
    conditions: Optional[str] = None
    output_type: str = "research_report"

    cost_mode: CostMode = CostMode.BALANCED
    verification_level: VerificationLevel = VerificationLevel.STANDARD
    output_length: OutputLength = OutputLength.NORMAL

    status: ProjectStatus = ProjectStatus.CREATED
    current_step: str = "프로젝트 생성"

    retry_count: int = 0
    max_retry: int = 1
    budget_cap: float = 1500.0
    estimated_cost: float = 0.0

    failure_reason: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
