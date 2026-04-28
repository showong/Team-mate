"""In-memory repositories for Phase 1.

Each repository is an in-process dict, intentionally simple. The interface
matches what we'd expect from a SQLAlchemy-backed implementation, so swapping
storage in Phase 2 only changes this file.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.schemas import (
    CostLog,
    DeputyOutput,
    JuniorOutput,
    Project,
    Review,
    Task,
)


# --- Project --------------------------------------------------------------


class ProjectRepository:
    def __init__(self) -> None:
        self._items: Dict[str, Project] = {}

    def save(self, project: Project) -> Project:
        self._items[project.project_id] = project
        return project

    def get(self, project_id: str) -> Optional[Project]:
        return self._items.get(project_id)

    def all(self) -> List[Project]:
        return list(self._items.values())


# --- Task -----------------------------------------------------------------


class TaskRepository:
    def __init__(self) -> None:
        self._items: Dict[str, Task] = {}

    def save(self, task: Task) -> Task:
        self._items[task.task_id] = task
        return task

    def get(self, task_id: str) -> Optional[Task]:
        return self._items.get(task_id)

    def list_for_project(self, project_id: str) -> List[Task]:
        return [t for t in self._items.values() if t.project_id == project_id]


# --- Output (junior + deputy) ---------------------------------------------


class OutputRepository:
    def __init__(self) -> None:
        self._juniors: Dict[str, JuniorOutput] = {}
        self._deputies: Dict[str, DeputyOutput] = {}

    def save_junior(self, output: JuniorOutput) -> JuniorOutput:
        self._juniors[output.output_id] = output
        return output

    def save_deputy(self, output: DeputyOutput) -> DeputyOutput:
        self._deputies[output.output_id] = output
        return output

    def list_juniors(self, project_id: str) -> List[JuniorOutput]:
        return [o for o in self._juniors.values() if o.project_id == project_id]

    def latest_deputy(self, project_id: str) -> Optional[DeputyOutput]:
        items = [o for o in self._deputies.values() if o.project_id == project_id]
        return items[-1] if items else None

    def list_deputies(self, project_id: str) -> List[DeputyOutput]:
        return [o for o in self._deputies.values() if o.project_id == project_id]

    def junior_for(self, project_id: str, assignee: str) -> Optional[JuniorOutput]:
        for o in reversed(list(self._juniors.values())):
            if o.project_id == project_id and o.assignee == assignee:
                return o
        return None


# --- Review ---------------------------------------------------------------


class ReviewRepository:
    def __init__(self) -> None:
        self._items: Dict[str, Review] = {}

    def save(self, review: Review) -> Review:
        self._items[review.review_id] = review
        return review

    def list_for_project(self, project_id: str) -> List[Review]:
        return [r for r in self._items.values() if r.project_id == project_id]

    def latest(self, project_id: str) -> Optional[Review]:
        reviews = self.list_for_project(project_id)
        return reviews[-1] if reviews else None


# --- Cost -----------------------------------------------------------------


class CostRepository:
    def __init__(self) -> None:
        self._items: List[CostLog] = []

    def save(self, log: CostLog) -> CostLog:
        self._items.append(log)
        return log

    def list_for_project(self, project_id: str) -> List[CostLog]:
        return [c for c in self._items if c.project_id == project_id]

    def total_for_project(self, project_id: str) -> float:
        return sum(c.estimated_cost for c in self._items if c.project_id == project_id)


# --- Bundle ---------------------------------------------------------------


@dataclass
class Repositories:
    projects: ProjectRepository = field(default_factory=ProjectRepository)
    tasks: TaskRepository = field(default_factory=TaskRepository)
    outputs: OutputRepository = field(default_factory=OutputRepository)
    reviews: ReviewRepository = field(default_factory=ReviewRepository)
    costs: CostRepository = field(default_factory=CostRepository)
