"""Circuit breaker tests."""

import uuid

from app.core.circuit_breaker import evaluate
from app.schemas.review import Decision, Review, ReviewScores


def _review(reason_code=None) -> Review:
    return Review(
        review_id=uuid.uuid4().hex,
        project_id="tm_test",
        scores=ReviewScores(accuracy=2, source_quality=2, logic=2, completeness=2, hallucination_risk=2),
        decision=Decision.REJECTED,
        feedback="test",
        rejection_reason_code=reason_code,
    )


def test_trips_when_retry_count_exceeds_max(sample_project):
    sample_project.retry_count = 1
    sample_project.max_retry = 1
    verdict = evaluate(sample_project, [])
    assert verdict.tripped


def test_trips_when_budget_would_exceed_cap(sample_project):
    sample_project.estimated_cost = 1490.0
    sample_project.budget_cap = 1500.0
    verdict = evaluate(sample_project, [], next_call_estimated_cost=20.0)
    assert verdict.tripped


def test_trips_when_same_rejection_code_repeats(sample_project):
    reviews = [_review("INSUFFICIENT_SOURCES"), _review("INSUFFICIENT_SOURCES")]
    verdict = evaluate(sample_project, reviews)
    assert verdict.tripped
    assert "INSUFFICIENT_SOURCES" in verdict.reason


def test_does_not_trip_when_within_limits(sample_project):
    sample_project.retry_count = 0
    sample_project.max_retry = 1
    sample_project.estimated_cost = 100.0
    sample_project.budget_cap = 1500.0
    verdict = evaluate(sample_project, [_review("INSUFFICIENT_SOURCES")])
    assert not verdict.tripped


def test_trips_on_repeated_model_failures(sample_project):
    verdict = evaluate(sample_project, [], consecutive_failures=3)
    assert verdict.tripped
