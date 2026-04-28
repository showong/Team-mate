"""Outputs produced by each agent + transport packets between roles."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class Source(BaseModel):
    title: str
    url: Optional[str] = None
    summary: Optional[str] = None


class SummaryPacket(BaseModel):
    """Junior → Deputy 전달용 패킷. 토큰 다이어트의 핵심."""

    role: str
    task: str
    key_findings: List[str] = Field(default_factory=list)
    sources: List[Source] = Field(default_factory=list)
    uncertain_points: List[str] = Field(default_factory=list)
    recommended_next_action: Optional[str] = None


class JuniorOutput(BaseModel):
    output_id: str
    project_id: str
    task_id: str
    assignee: str  # e.g. junior_a
    task_scope: str
    content: str
    summary_packet: SummaryPacket
    sources: List[Source] = Field(default_factory=list)
    uncertain_points: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class KeyClaim(BaseModel):
    claim: str
    evidence: Optional[str] = None
    source: Optional[str] = None
    confidence: str = "medium"  # low | medium | high


class ExcludedItem(BaseModel):
    item: str
    reason: str


class ReviewPackage(BaseModel):
    """Deputy → Sub-leader 전달용 패킷."""

    draft_report: str
    key_claims: List[KeyClaim] = Field(default_factory=list)
    excluded_items: List[ExcludedItem] = Field(default_factory=list)
    risk_points: List[str] = Field(default_factory=list)


class DeputyOutput(BaseModel):
    output_id: str
    project_id: str
    task_id: str
    draft_report: str
    review_package: ReviewPackage
    junior_attribution: dict = Field(default_factory=dict)  # junior_id -> reflected_summary
    excluded_items: List[ExcludedItem] = Field(default_factory=list)
    follow_up_questions: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
