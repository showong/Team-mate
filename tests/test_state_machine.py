"""State machine tests."""

import pytest

from app.core.state_machine import IllegalStateTransition, is_terminal, transition
from app.schemas.project import ProjectStatus


def test_happy_path_transitions(sample_project):
    p = sample_project
    for target in [
        ProjectStatus.ROUTING,
        ProjectStatus.TASK_SPLITTING,
        ProjectStatus.COLLECTING_SOURCES,
        ProjectStatus.RESEARCHING,
        ProjectStatus.SUMMARIZING,
        ProjectStatus.REVIEWING,
        ProjectStatus.QUALITY_CHECKING,
        ProjectStatus.FINALIZING,
        ProjectStatus.COMPLETED,
    ]:
        transition(p, target)
        assert p.status == target


def test_illegal_transition_raises(sample_project):
    p = sample_project
    with pytest.raises(IllegalStateTransition):
        transition(p, ProjectStatus.COMPLETED)  # CREATED → COMPLETED is not allowed


def test_any_status_can_go_failed(sample_project):
    p = sample_project
    transition(p, ProjectStatus.FAILED)
    assert p.status == ProjectStatus.FAILED


def test_terminal_statuses(sample_project):
    p = sample_project
    assert not is_terminal(p.status)
    transition(p, ProjectStatus.ROUTING)
    transition(p, ProjectStatus.TASK_SPLITTING)
    transition(p, ProjectStatus.RESEARCHING)
    transition(p, ProjectStatus.SUMMARIZING)
    transition(p, ProjectStatus.REVIEWING)
    transition(p, ProjectStatus.QUALITY_CHECKING)
    transition(p, ProjectStatus.FINALIZING)
    transition(p, ProjectStatus.COMPLETED)
    assert is_terminal(p.status)


def test_retry_path(sample_project):
    p = sample_project
    transition(p, ProjectStatus.ROUTING)
    transition(p, ProjectStatus.TASK_SPLITTING)
    transition(p, ProjectStatus.RESEARCHING)
    transition(p, ProjectStatus.SUMMARIZING)
    transition(p, ProjectStatus.REVIEWING)
    transition(p, ProjectStatus.QUALITY_CHECKING)
    transition(p, ProjectStatus.RETRYING)
    transition(p, ProjectStatus.REVIEWING)
    transition(p, ProjectStatus.QUALITY_CHECKING)
    transition(p, ProjectStatus.FINALIZING)
    transition(p, ProjectStatus.COMPLETED)
    assert p.status == ProjectStatus.COMPLETED


def test_current_step_label_is_updated(sample_project):
    p = sample_project
    transition(p, ProjectStatus.ROUTING)
    assert "분석" in p.current_step
