"""Workflow Orchestrator.

End-to-end project execution. Owns the state-machine transitions and is the
only module that calls the agents in business order. Decision Engine, Retry
Manager and Circuit Breaker are consulted between stages but never invoked
out of band.

The orchestrator is intentionally synchronous in Phase 1; queueing is a
Phase-2 concern.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import List, Optional

from app.agents.agenda_router import AgendaRouter, RoutingDecision
from app.agents.deputy_agent import DeputyAgent
from app.agents.junior_agent import JuniorAgent
from app.agents.subleader_agent import SubleaderAgent
from app.agents.task_splitter import TaskSplitter
from app.config import Settings, get_settings
from app.core import circuit_breaker, decision_engine, retry_manager, state_machine
from app.core.cost_tracker import CostTracker
from app.llm.base_client import BaseLLMClient
from app.llm.factory import build_llm_client
from app.schemas import (
    DeputyOutput,
    JuniorOutput,
    Project,
    ProjectCreate,
    ProjectStatus,
    Review,
    Task,
    TaskStatus,
)
from app.schemas.project import CostMode
from app.schemas.review import RetryTargetRole
from app.services.log_service import LogService, ProjectLog
from app.services.report_service import FinalReport, ReportService
from app.services.source_service import SourceService
from app.storage import Repositories, get_repositories
from app.utils.logger import get_logger


_LOG = get_logger(__name__)


# Cost-mode → max_retry mapping (PHASE 1 spec, section 8.3).
_RETRY_BY_MODE = {
    CostMode.LOW_COST: 1,
    CostMode.BALANCED: 1,
    CostMode.HIGH_QUALITY: 2,
    CostMode.TEST: 3,
}


@dataclass
class WorkflowResult:
    project: Project
    report: Optional[FinalReport]
    review: Optional[Review]
    routing: Optional[RoutingDecision]
    log: ProjectLog


class Orchestrator:
    def __init__(
        self,
        repos: Optional[Repositories] = None,
        llm: Optional[BaseLLMClient] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._repos = repos or get_repositories()
        self._llm = llm or build_llm_client(self._settings)
        self._cost = CostTracker(self._repos)

        self._router = AgendaRouter(self._llm, self._cost, self._settings)
        self._splitter = TaskSplitter(self._llm, self._cost, self._settings)
        self._junior = JuniorAgent(self._llm, self._cost, self._settings)
        self._deputy = DeputyAgent(self._llm, self._cost, self._settings)
        self._subleader = SubleaderAgent(self._llm, self._cost, self._settings)

        self._sources = SourceService()
        self._reports = ReportService()
        self._logs = LogService(self._repos)

    # ----- public API -----

    def create_project(self, payload: ProjectCreate) -> Project:
        project_id = f"tm_{uuid.uuid4().hex[:8]}"
        project = Project(
            project_id=project_id,
            agenda=payload.agenda,
            purpose=payload.purpose,
            conditions=payload.conditions,
            cost_mode=payload.cost_mode,
            verification_level=payload.verification_level,
            output_length=payload.output_length,
            max_retry=_RETRY_BY_MODE.get(payload.cost_mode, self._settings.default_max_retry),
            budget_cap=self._settings.default_budget_cap,
        )
        self._repos.projects.save(project)
        _LOG.info("project_created project_id=%s", project_id)
        return project

    def run_project(self, project_id: str) -> WorkflowResult:
        project = self._require(project_id)
        try:
            return self._run(project)
        except Exception as exc:  # last-resort safety net
            _LOG.exception("orchestrator_failure project_id=%s", project_id)
            project.status = ProjectStatus.FAILED
            project.failure_reason = str(exc)
            self._repos.projects.save(project)
            return WorkflowResult(
                project=project,
                report=None,
                review=self._repos.reviews.latest(project_id),
                routing=None,
                log=self._logs.collect(project_id),
            )

    # ----- main loop -----

    def _run(self, project: Project) -> WorkflowResult:
        # 1. Route
        state_machine.transition(project, ProjectStatus.ROUTING)
        self._repos.projects.save(project)
        routing = self._router.run(project)
        _LOG.info(
            "agenda_routed project_id=%s difficulty=%s juniors=%d",
            project.project_id, routing.difficulty, routing.junior_count,
        )

        # 2. Split
        state_machine.transition(project, ProjectStatus.TASK_SPLITTING)
        self._repos.projects.save(project)
        tasks = self._splitter.run(project, routing)
        for t in tasks:
            self._repos.tasks.save(t)

        # 3. Source collection (Phase 1: passthrough)
        state_machine.transition(project, ProjectStatus.COLLECTING_SOURCES)
        self._repos.projects.save(project)
        source_material = self._sources.collect(project.agenda, project.conditions)

        # 4. Junior research
        state_machine.transition(project, ProjectStatus.RESEARCHING)
        self._repos.projects.save(project)
        junior_outputs = self._run_juniors(project, tasks, source_material)

        # 5. Summary packets are part of JuniorOutput already → mark stage.
        state_machine.transition(project, ProjectStatus.SUMMARIZING)
        self._repos.projects.save(project)

        # 6. Deputy review
        state_machine.transition(project, ProjectStatus.REVIEWING)
        self._repos.projects.save(project)
        deputy_output = self._deputy.run(project, junior_outputs)
        self._repos.outputs.save_deputy(deputy_output)

        # 7. Sub-leader QA
        state_machine.transition(project, ProjectStatus.QUALITY_CHECKING)
        self._repos.projects.save(project)
        review = self._subleader.run(project, deputy_output)
        self._repos.reviews.save(review)
        outcome = decision_engine.evaluate(review)
        _LOG.info(
            "review_decision project_id=%s decision=%s avg=%.2f",
            project.project_id, outcome.decision.value, outcome.average_score,
        )

        circuit_break_reason: Optional[str] = None

        # 8. Retry loop
        while outcome.needs_retry:
            verdict = circuit_breaker.evaluate(project, self._repos.reviews.list_for_project(project.project_id))
            if verdict.tripped:
                circuit_break_reason = verdict.reason
                _LOG.warning("circuit_breaker_tripped project_id=%s reason=%s",
                             project.project_id, verdict.reason)
                break

            plan = retry_manager.build_plan(project, review)
            if not plan.can_retry:
                circuit_break_reason = plan.reason
                break

            state_machine.transition(project, ProjectStatus.RETRYING)
            retry_manager.increment(project)
            self._repos.projects.save(project)
            _LOG.info(
                "retry_started project_id=%s attempt=%d targets=%d",
                project.project_id, project.retry_count, len(plan.targets),
            )

            junior_outputs = self._apply_partial_retry(project, tasks, junior_outputs, plan.targets, source_material)

            state_machine.transition(project, ProjectStatus.REVIEWING)
            self._repos.projects.save(project)
            deputy_output = self._deputy.run(project, junior_outputs, previous_review=review)
            self._repos.outputs.save_deputy(deputy_output)

            state_machine.transition(project, ProjectStatus.QUALITY_CHECKING)
            self._repos.projects.save(project)
            review = self._subleader.run(project, deputy_output)
            self._repos.reviews.save(review)
            outcome = decision_engine.evaluate(review)
            _LOG.info(
                "review_decision project_id=%s decision=%s avg=%.2f (retry %d)",
                project.project_id, outcome.decision.value, outcome.average_score,
                project.retry_count,
            )

        # 9. Conditional approved → deputy revises only (cheap path)
        if outcome.needs_minor_revision and not circuit_break_reason:
            _LOG.info("conditional_revision project_id=%s", project.project_id)
            deputy_output = self._deputy.run(project, junior_outputs, previous_review=review)
            self._repos.outputs.save_deputy(deputy_output)

        # 10. Finalise
        state_machine.transition(project, ProjectStatus.FINALIZING)
        self._repos.projects.save(project)
        report = self._reports.build(
            project,
            deputy_output,
            review,
            junior_outputs,
            circuit_break_reason=circuit_break_reason,
        )

        state_machine.transition(project, ProjectStatus.COMPLETED)
        self._repos.projects.save(project)

        return WorkflowResult(
            project=project,
            report=report,
            review=review,
            routing=routing,
            log=self._logs.collect(project.project_id),
        )

    # ----- stage helpers -----

    def _run_juniors(
        self, project: Project, tasks: List[Task], source_material: str
    ) -> List[JuniorOutput]:
        outputs: List[JuniorOutput] = []
        for task in tasks:
            task.status = TaskStatus.RUNNING
            self._repos.tasks.save(task)

            output = self._junior.run(project, task, source_material=source_material or None)
            self._repos.outputs.save_junior(output)

            task.status = TaskStatus.SUBMITTED
            self._repos.tasks.save(task)
            outputs.append(output)
        return outputs

    def _apply_partial_retry(
        self,
        project: Project,
        tasks: List[Task],
        junior_outputs: List[JuniorOutput],
        targets,
        source_material: str,
    ) -> List[JuniorOutput]:
        """Re-run only the roles named in `targets`.

        Deputy retries are handled by the surrounding loop (it always re-runs
        the deputy on the next iteration). Here we only need to re-run any
        junior whose work was flagged.
        """
        junior_targets = [t for t in targets if t.role == RetryTargetRole.JUNIOR]
        if not junior_targets:
            return junior_outputs

        by_assignee = {o.assignee: o for o in junior_outputs}
        for target in junior_targets:
            task = next(
                (t for t in tasks if t.assignee == target.assignee),
                None,
            )
            if task is None:
                continue
            task.status = TaskStatus.RETRYING
            task.retry_count += 1
            task.notes = target.reason
            self._repos.tasks.save(task)

            output = self._junior.run(project, task, source_material=source_material or None)
            self._repos.outputs.save_junior(output)
            by_assignee[task.assignee] = output

            task.status = TaskStatus.SUBMITTED
            self._repos.tasks.save(task)

        # Preserve original task ordering.
        return [by_assignee[t.assignee] for t in tasks if t.assignee in by_assignee]

    # ----- misc -----

    def _require(self, project_id: str) -> Project:
        project = self._repos.projects.get(project_id)
        if project is None:
            raise LookupError(f"Unknown project: {project_id}")
        return project
