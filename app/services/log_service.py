"""Project log assembly — exposes the full audit trail for `/projects/:id/logs`."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from app.schemas import CostLog, DeputyOutput, JuniorOutput, Review, Task
from app.storage import Repositories


@dataclass
class ProjectLog:
    project_id: str
    tasks: List[Task] = field(default_factory=list)
    junior_outputs: List[JuniorOutput] = field(default_factory=list)
    deputy_outputs: List[DeputyOutput] = field(default_factory=list)
    reviews: List[Review] = field(default_factory=list)
    costs: List[CostLog] = field(default_factory=list)


class LogService:
    def __init__(self, repos: Repositories) -> None:
        self._repos = repos

    def collect(self, project_id: str) -> ProjectLog:
        return ProjectLog(
            project_id=project_id,
            tasks=self._repos.tasks.list_for_project(project_id),
            junior_outputs=self._repos.outputs.list_juniors(project_id),
            deputy_outputs=self._repos.outputs.list_deputies(project_id),
            reviews=self._repos.reviews.list_for_project(project_id),
            costs=self._repos.costs.list_for_project(project_id),
        )
