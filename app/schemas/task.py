"""Task-level schema (a unit of work assigned to a role)."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TaskRole(str, Enum):
    JUNIOR = "junior"
    DEPUTY = "deputy"
    SUBLEADER = "subleader"
    ROUTER = "router"
    SPLITTER = "splitter"


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    CONDITIONAL_APPROVED = "CONDITIONAL_APPROVED"
    REJECTED = "REJECTED"
    RETRYING = "RETRYING"
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"


class Task(BaseModel):
    task_id: str
    project_id: str
    role: TaskRole
    assignee: str  # e.g. "junior_a", "deputy", "subleader"
    task_scope: str
    status: TaskStatus = TaskStatus.PENDING
    retry_count: int = 0
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
