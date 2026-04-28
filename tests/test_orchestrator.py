"""Orchestrator integration tests using the Mock LLM client."""

import pytest

from app.core.orchestrator import Orchestrator
from app.llm.mock_client import MockLLMClient
from app.schemas import ProjectCreate, ProjectStatus
from app.schemas.project import CostMode
from app.schemas.review import Decision
from app.storage.database import get_repositories, reset_repositories


def _make_orch(force_decision=None, force_failure_steps=None):
    reset_repositories()
    repos = get_repositories()
    llm = MockLLMClient(
        force_decision=force_decision,
        force_failure_steps=force_failure_steps,
    )
    return Orchestrator(repos=repos, llm=llm), repos


def _payload(**kwargs):
    defaults = dict(
        agenda="AI 트레이너 시장 현황 조사",
        purpose="커리어 확장",
        cost_mode=CostMode.BALANCED,
    )
    defaults.update(kwargs)
    return ProjectCreate(**defaults)


# ----- happy path -----

def test_full_workflow_approved():
    orch, repos = _make_orch(force_decision="APPROVED")
    project = orch.create_project(_payload())
    result = orch.run_project(project.project_id)

    assert result.project.status == ProjectStatus.COMPLETED
    assert result.report is not None
    assert not result.report.is_partial
    assert result.review.decision == Decision.APPROVED
    assert result.project.retry_count == 0


def test_full_workflow_conditional_approved():
    orch, repos = _make_orch(force_decision="CONDITIONAL_APPROVED")
    project = orch.create_project(_payload())
    result = orch.run_project(project.project_id)

    assert result.project.status == ProjectStatus.COMPLETED
    assert result.report is not None


# ----- retry path -----

def test_rejected_triggers_one_retry_then_completes():
    """First sub-leader call → REJECTED; second → APPROVED after retry."""

    subleader_calls = {"n": 0}

    class _TrackedMock(MockLLMClient):
        def complete(self, prompt, **kw):
            if "ROLE: SUBLEADER_QA" in prompt[:400]:
                subleader_calls["n"] += 1
                self.force_decision = "REJECTED" if subleader_calls["n"] == 1 else "APPROVED"
            return super().complete(prompt, **kw)

    reset_repositories()
    repos = get_repositories()
    llm = _TrackedMock()
    orch = Orchestrator(repos=repos, llm=llm)

    project = orch.create_project(_payload(cost_mode=CostMode.BALANCED))
    result = orch.run_project(project.project_id)

    assert result.project.status == ProjectStatus.COMPLETED
    assert result.project.retry_count == 1
    assert subleader_calls["n"] == 2


def test_rejected_exceeds_max_retry_activates_circuit_breaker():
    """Persistent REJECTED should trip the circuit breaker and still produce a partial report."""
    orch, repos = _make_orch(force_decision="REJECTED")
    # max_retry=1 means one retry allowed; both sub-leader calls REJECT → circuit breaks.
    project = orch.create_project(_payload(cost_mode=CostMode.BALANCED))
    result = orch.run_project(project.project_id)

    assert result.project.status == ProjectStatus.COMPLETED
    assert result.report is not None
    assert result.report.is_partial


# ----- cost tracking -----

def test_cost_is_recorded_after_run():
    orch, repos = _make_orch(force_decision="APPROVED")
    project = orch.create_project(_payload())
    orch.run_project(project.project_id)
    costs = repos.costs.list_for_project(project.project_id)
    assert len(costs) >= 5  # router, splitter, 3 juniors, deputy, subleader
    assert repos.costs.total_for_project(project.project_id) >= 0


# ----- storage -----

def test_tasks_and_outputs_are_persisted():
    orch, repos = _make_orch(force_decision="APPROVED")
    project = orch.create_project(_payload())
    orch.run_project(project.project_id)

    tasks = repos.tasks.list_for_project(project.project_id)
    assert len(tasks) == 3  # 3 juniors

    juniors = repos.outputs.list_juniors(project.project_id)
    assert len(juniors) == 3

    deputy = repos.outputs.latest_deputy(project.project_id)
    assert deputy is not None

    review = repos.reviews.latest(project.project_id)
    assert review is not None
    assert review.decision == Decision.APPROVED


# ----- unknown project -----

def test_run_unknown_project_raises():
    orch, _ = _make_orch()
    with pytest.raises(LookupError):
        orch.run_project("nonexistent_id")
