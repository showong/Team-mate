"""Report, log, and cost endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.services.evaluation_service import EvaluationService
from app.services.log_service import LogService
from app.services.report_service import ReportService
from app.storage.database import get_repositories

router = APIRouter(prefix="/projects", tags=["reports"])


def _require(project_id: str):
    repos = get_repositories()
    project = repos.projects.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id!r} not found.")
    return project, repos


@router.get("/{project_id}/report")
def get_report(project_id: str) -> dict:
    project, repos = _require(project_id)

    deputy = repos.outputs.latest_deputy(project_id)
    if deputy is None:
        raise HTTPException(status_code=404, detail="Report not generated yet.")

    review = repos.reviews.latest(project_id)
    juniors = repos.outputs.list_juniors(project_id)

    svc = ReportService()
    report = svc.build(project, deputy, review, juniors)
    return {
        "project_id": project_id,
        "is_partial": report.is_partial,
        "limits": report.limits,
        "markdown": report.markdown,
    }


@router.get("/{project_id}/logs")
def get_logs(project_id: str) -> dict:
    _, repos = _require(project_id)
    svc = LogService(repos)
    log = svc.collect(project_id)
    return {
        "project_id": project_id,
        "tasks": [t.model_dump() for t in log.tasks],
        "junior_outputs": [
            {
                "output_id": o.output_id,
                "assignee": o.assignee,
                "task_scope": o.task_scope,
                "summary_packet": o.summary_packet.model_dump(),
                "uncertain_points": o.uncertain_points,
            }
            for o in log.junior_outputs
        ],
        "deputy_outputs": [
            {
                "output_id": o.output_id,
                "risk_points": o.review_package.risk_points,
                "follow_up_questions": o.follow_up_questions,
            }
            for o in log.deputy_outputs
        ],
        "reviews": [
            {
                "review_id": r.review_id,
                "decision": r.decision.value,
                "average_score": r.scores.average,
                "feedback": r.feedback,
            }
            for r in log.reviews
        ],
    }


@router.get("/{project_id}/costs")
def get_costs(project_id: str) -> dict:
    _, repos = _require(project_id)
    costs = repos.costs.list_for_project(project_id)
    total = repos.costs.total_for_project(project_id)
    svc = EvaluationService(repos)
    evaluation = svc.summarise(project_id)
    return {
        "project_id": project_id,
        "total_estimated_cost": round(total, 4),
        "breakdown": [c.model_dump() for c in costs],
        "evaluation": {
            "review_count": evaluation.review_count,
            "retry_count": evaluation.retry_count,
            "final_average_score": evaluation.final_average_score,
            "final_decision": evaluation.final_decision,
        },
    }
