"""Per-project cost ledger.

Wraps `CostRepository` so callers (orchestrator + agents) only need a single
verb: `record(...)`. Also keeps `Project.estimated_cost` in sync because the
circuit breaker reads it.
"""

from __future__ import annotations

import uuid

from app.llm.base_client import LLMResponse
from app.schemas import CostLog, Project
from app.storage import Repositories


class CostTracker:
    def __init__(self, repos: Repositories) -> None:
        self._repos = repos

    def record(self, project: Project, step: str, response: LLMResponse) -> CostLog:
        log = CostLog(
            cost_id=f"cost_{uuid.uuid4().hex[:8]}",
            project_id=project.project_id,
            step=step,
            model_name=response.model_name,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            estimated_cost=response.estimated_cost,
        )
        self._repos.costs.save(log)
        project.estimated_cost = round(project.estimated_cost + response.estimated_cost, 4)
        self._repos.projects.save(project)
        return log

    def total(self, project_id: str) -> float:
        return self._repos.costs.total_for_project(project_id)
