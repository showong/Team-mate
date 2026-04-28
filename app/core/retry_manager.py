"""Decides whether (and how) to retry a rejected workflow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from app.schemas import Project, Review
from app.schemas.review import RetryTarget, RetryTargetRole


@dataclass
class RetryPlan:
    can_retry: bool
    targets: List[RetryTarget]
    reason: str


def can_retry(project: Project) -> bool:
    return project.retry_count < project.max_retry


def build_plan(project: Project, review: Review) -> RetryPlan:
    """Translate review feedback into a partial-retry plan.

    Phase 1 rule: if the sub-leader provided explicit retry_targets, use them
    verbatim. Otherwise default to a deputy-only revision so we don't burn
    junior tokens unnecessarily.
    """

    if not can_retry(project):
        return RetryPlan(
            can_retry=False,
            targets=[],
            reason=f"max_retry ({project.max_retry}) 도달",
        )

    if review.retry_targets:
        return RetryPlan(
            can_retry=True,
            targets=review.retry_targets,
            reason=review.feedback or "subleader requested retry",
        )

    return RetryPlan(
        can_retry=True,
        targets=[
            RetryTarget(
                role=RetryTargetRole.DEPUTY,
                assignee="deputy",
                reason=review.feedback or "deputy revision required",
            )
        ],
        reason="default deputy-only revision",
    )


def increment(project: Project) -> Project:
    project.retry_count += 1
    return project
