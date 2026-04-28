"""Project lifecycle endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.orchestrator import Orchestrator
from app.schemas import ProjectCreate, ProjectStatus
from app.storage.database import get_repositories

router = APIRouter(prefix="/projects", tags=["projects"])


def _get_orchestrator() -> Orchestrator:
    return Orchestrator(repos=get_repositories())


@router.post("", status_code=201)
def create_project(payload: ProjectCreate) -> dict:
    """Create a new research project (does NOT run the workflow yet)."""
    orch = _get_orchestrator()
    project = orch.create_project(payload)
    return {"project_id": project.project_id, "status": project.status.value}


@router.post("/{project_id}/run")
def run_project(project_id: str) -> dict:
    """Execute the full workflow synchronously and return when done."""
    repos = get_repositories()
    if repos.projects.get(project_id) is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id!r} not found.")

    orch = Orchestrator(repos=repos)
    result = orch.run_project(project_id)
    return {
        "project_id": result.project.project_id,
        "status": result.project.status.value,
        "report_path": f"/projects/{project_id}/report",
        "estimated_cost": result.project.estimated_cost,
    }


@router.get("/{project_id}")
def get_project(project_id: str) -> dict:
    repos = get_repositories()
    project = repos.projects.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id!r} not found.")
    return {
        "project_id": project.project_id,
        "agenda": project.agenda,
        "status": project.status.value,
        "current_step": project.current_step,
        "retry_count": project.retry_count,
        "estimated_cost": project.estimated_cost,
        "created_at": project.created_at.isoformat(),
    }
