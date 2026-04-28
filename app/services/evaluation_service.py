"""Evaluation summary — collects per-project quality + cost stats."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.storage import Repositories


@dataclass
class EvaluationSummary:
    project_id: str
    total_cost: float
    review_count: int
    final_average_score: Optional[float]
    final_decision: Optional[str]
    retry_count: int


class EvaluationService:
    def __init__(self, repos: Repositories) -> None:
        self._repos = repos

    def summarise(self, project_id: str) -> EvaluationSummary:
        project = self._repos.projects.get(project_id)
        reviews = self._repos.reviews.list_for_project(project_id)
        latest = reviews[-1] if reviews else None

        return EvaluationSummary(
            project_id=project_id,
            total_cost=self._repos.costs.total_for_project(project_id),
            review_count=len(reviews),
            final_average_score=round(latest.scores.average, 2) if latest else None,
            final_decision=latest.decision.value if latest else None,
            retry_count=project.retry_count if project else 0,
        )
