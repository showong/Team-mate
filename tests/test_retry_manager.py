"""Retry manager tests."""

import uuid

from app.core import retry_manager
from app.schemas.review import Decision, Review, ReviewScores, RetryTarget, RetryTargetRole


def _make_review(decision: Decision, targets=None, reason_code=None) -> Review:
    return Review(
        review_id=uuid.uuid4().hex,
        project_id="tm_test",
        scores=ReviewScores(accuracy=3, source_quality=2, logic=3, completeness=3, hallucination_risk=2),
        decision=decision,
        feedback="test",
        retry_targets=targets or [],
        rejection_reason_code=reason_code,
    )


def test_can_retry_when_under_limit(sample_project):
    sample_project.retry_count = 0
    sample_project.max_retry = 1
    assert retry_manager.can_retry(sample_project)


def test_cannot_retry_when_at_limit(sample_project):
    sample_project.retry_count = 1
    sample_project.max_retry = 1
    assert not retry_manager.can_retry(sample_project)


def test_build_plan_uses_review_targets(sample_project):
    targets = [RetryTarget(role=RetryTargetRole.JUNIOR, assignee="junior_a", reason="출처 부족")]
    review = _make_review(Decision.REJECTED, targets=targets)
    plan = retry_manager.build_plan(sample_project, review)
    assert plan.can_retry
    assert any(t.assignee == "junior_a" for t in plan.targets)


def test_build_plan_defaults_to_deputy(sample_project):
    review = _make_review(Decision.REJECTED)  # no explicit retry_targets
    plan = retry_manager.build_plan(sample_project, review)
    assert plan.can_retry
    assert all(t.role == RetryTargetRole.DEPUTY for t in plan.targets)


def test_build_plan_returns_cannot_retry_when_exhausted(sample_project):
    sample_project.retry_count = 1
    sample_project.max_retry = 1
    review = _make_review(Decision.REJECTED)
    plan = retry_manager.build_plan(sample_project, review)
    assert not plan.can_retry


def test_increment_raises_retry_count(sample_project):
    sample_project.retry_count = 0
    retry_manager.increment(sample_project)
    assert sample_project.retry_count == 1
