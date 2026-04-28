"""Maps a sub-leader review to the next workflow action."""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas import Decision, Review


@dataclass
class DecisionOutcome:
    decision: Decision
    needs_retry: bool
    needs_minor_revision: bool  # CONDITIONAL_APPROVED → deputy revises only
    average_score: float


# Phase 1 thresholds, matching the spec.
APPROVE_THRESHOLD = 4.0
CONDITIONAL_THRESHOLD = 3.5


def evaluate(review: Review) -> DecisionOutcome:
    avg = review.scores.average
    if avg >= APPROVE_THRESHOLD:
        decision = Decision.APPROVED
    elif avg >= CONDITIONAL_THRESHOLD:
        decision = Decision.CONDITIONAL_APPROVED
    else:
        decision = Decision.REJECTED

    # Honour explicit decision from the review when it's stricter than ours
    # (the sub-leader can over-rule on qualitative grounds even if scores
    # look fine — e.g. obvious off-topic).
    if review.decision == Decision.REJECTED:
        decision = Decision.REJECTED

    return DecisionOutcome(
        decision=decision,
        needs_retry=decision == Decision.REJECTED,
        needs_minor_revision=decision == Decision.CONDITIONAL_APPROVED,
        average_score=round(avg, 2),
    )
