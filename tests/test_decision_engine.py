"""Decision engine tests."""

import uuid
from datetime import datetime

import pytest

from app.core.decision_engine import evaluate, APPROVE_THRESHOLD, CONDITIONAL_THRESHOLD
from app.schemas.review import Decision, Review, ReviewScores


def _review(accuracy, source_quality, logic, completeness, hallucination_risk, decision=None):
    scores = ReviewScores(
        accuracy=accuracy,
        source_quality=source_quality,
        logic=logic,
        completeness=completeness,
        hallucination_risk=hallucination_risk,
    )
    inferred = Decision.APPROVED
    avg = scores.average
    if avg < CONDITIONAL_THRESHOLD:
        inferred = Decision.REJECTED
    elif avg < APPROVE_THRESHOLD:
        inferred = Decision.CONDITIONAL_APPROVED

    return Review(
        review_id=f"r_{uuid.uuid4().hex[:6]}",
        project_id="tm_test",
        scores=scores,
        decision=decision or inferred,
        feedback="test feedback",
    )


def test_approve_when_all_5(sample_project):
    review = _review(5, 5, 5, 5, 5)
    outcome = evaluate(review)
    assert outcome.decision == Decision.APPROVED
    assert not outcome.needs_retry
    assert not outcome.needs_minor_revision


def test_conditional_approved_avg_3_8(sample_project):
    # avg = (4+4+4+4+3) / 5 = 3.8
    review = _review(4, 4, 4, 4, 3, decision=Decision.CONDITIONAL_APPROVED)
    outcome = evaluate(review)
    assert outcome.decision == Decision.CONDITIONAL_APPROVED
    assert outcome.needs_minor_revision
    assert not outcome.needs_retry


def test_rejected_when_low_scores(sample_project):
    # avg = (2+2+3+3+2) / 5 = 2.4
    review = _review(2, 2, 3, 3, 2, decision=Decision.REJECTED)
    outcome = evaluate(review)
    assert outcome.decision == Decision.REJECTED
    assert outcome.needs_retry
    assert not outcome.needs_minor_revision


def test_explicit_rejected_overrides_good_scores():
    """Sub-leader can manually REJECT even if scores are 4+."""
    review = _review(5, 5, 5, 4, 5, decision=Decision.REJECTED)
    outcome = evaluate(review)
    assert outcome.decision == Decision.REJECTED
    assert outcome.needs_retry
