"""Task Splitter — slices the agenda into per-junior scopes."""

from __future__ import annotations

import uuid
from typing import List

from app.agents.agenda_router import RoutingDecision
from app.agents.base_agent import BaseAgent
from app.schemas import Project, Task
from app.schemas.task import TaskRole, TaskStatus


class TaskSplitter(BaseAgent):
    prompt_file = "task_splitter.txt"
    step_name = "task_splitting"
    model_setting = "llm_model_router"

    def run(self, project: Project, routing: RoutingDecision) -> List[Task]:
        prompt = self._render(
            {
                "agenda": project.agenda,
                "purpose": project.purpose or "",
                "conditions": project.conditions or "",
                "junior_count": routing.junior_count,
            }
        )
        data = self._call_json(project, prompt, max_tokens=500)
        raw_tasks = data.get("tasks", [])
        if not raw_tasks:
            raise ValueError("Task splitter returned no tasks.")

        tasks: List[Task] = []
        for raw in raw_tasks[: routing.junior_count]:
            tasks.append(
                Task(
                    task_id=f"task_{uuid.uuid4().hex[:8]}",
                    project_id=project.project_id,
                    role=TaskRole.JUNIOR,
                    assignee=raw["assignee"],
                    task_scope=raw["task_scope"],
                    status=TaskStatus.PENDING,
                )
            )
        return tasks
