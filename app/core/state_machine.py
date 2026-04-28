"""Project state-machine guard.

Keeps `Project.status` transitions tightly constrained so a bug elsewhere
cannot push a project into an invalid step. Every business module flips the
status through `transition()` rather than mutating `project.status` directly.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Set

from app.schemas import Project, ProjectStatus


ALLOWED_TRANSITIONS: Dict[ProjectStatus, Set[ProjectStatus]] = {
    ProjectStatus.CREATED: {ProjectStatus.ROUTING, ProjectStatus.FAILED},
    ProjectStatus.ROUTING: {ProjectStatus.TASK_SPLITTING, ProjectStatus.FAILED},
    ProjectStatus.TASK_SPLITTING: {
        ProjectStatus.COLLECTING_SOURCES,
        ProjectStatus.RESEARCHING,
        ProjectStatus.FAILED,
    },
    ProjectStatus.COLLECTING_SOURCES: {ProjectStatus.RESEARCHING, ProjectStatus.FAILED},
    ProjectStatus.RESEARCHING: {ProjectStatus.SUMMARIZING, ProjectStatus.FAILED},
    ProjectStatus.SUMMARIZING: {ProjectStatus.REVIEWING, ProjectStatus.FAILED},
    ProjectStatus.REVIEWING: {ProjectStatus.QUALITY_CHECKING, ProjectStatus.FAILED},
    ProjectStatus.QUALITY_CHECKING: {
        ProjectStatus.FINALIZING,
        ProjectStatus.RETRYING,
        ProjectStatus.USER_INTERVENTION_REQUIRED,
        ProjectStatus.FAILED,
    },
    ProjectStatus.RETRYING: {
        ProjectStatus.RESEARCHING,
        ProjectStatus.REVIEWING,
        ProjectStatus.QUALITY_CHECKING,
        ProjectStatus.FAILED,
    },
    ProjectStatus.FINALIZING: {ProjectStatus.COMPLETED, ProjectStatus.FAILED},
    ProjectStatus.USER_INTERVENTION_REQUIRED: {
        ProjectStatus.FINALIZING,
        ProjectStatus.RETRYING,
        ProjectStatus.FAILED,
    },
    ProjectStatus.COMPLETED: set(),
    ProjectStatus.FAILED: set(),
}


_STEP_LABELS: Dict[ProjectStatus, str] = {
    ProjectStatus.CREATED: "프로젝트 생성",
    ProjectStatus.ROUTING: "아젠다 분석 중",
    ProjectStatus.TASK_SPLITTING: "업무 분해 중",
    ProjectStatus.COLLECTING_SOURCES: "자료 수집 중",
    ProjectStatus.RESEARCHING: "주임 조사 중",
    ProjectStatus.SUMMARIZING: "요약 패킷 생성 중",
    ProjectStatus.REVIEWING: "대리 검토 중",
    ProjectStatus.QUALITY_CHECKING: "부팀장 품질검수 중",
    ProjectStatus.RETRYING: "재작업 중",
    ProjectStatus.FINALIZING: "최종 보고서 생성 중",
    ProjectStatus.COMPLETED: "완료",
    ProjectStatus.FAILED: "실패",
    ProjectStatus.USER_INTERVENTION_REQUIRED: "사용자 개입 필요",
}


class IllegalStateTransition(RuntimeError):
    pass


def transition(project: Project, target: ProjectStatus) -> Project:
    if target not in ALLOWED_TRANSITIONS.get(project.status, set()):
        raise IllegalStateTransition(
            f"{project.project_id}: {project.status.value} → {target.value} is not allowed."
        )
    project.status = target
    project.current_step = _STEP_LABELS[target]
    project.updated_at = datetime.utcnow()
    return project


def is_terminal(status: ProjectStatus) -> bool:
    return status in {ProjectStatus.COMPLETED, ProjectStatus.FAILED}
