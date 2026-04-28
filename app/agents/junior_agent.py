"""Junior Agent — first-pass research."""

from __future__ import annotations

import uuid
from typing import Optional

from app.agents.base_agent import BaseAgent
from app.schemas import JuniorOutput, Project, Task
from app.schemas.output import Source, SummaryPacket


class JuniorAgent(BaseAgent):
    prompt_file = "junior_research.txt"
    step_name = "junior_research"
    model_setting = "llm_model_junior"

    def run(self, project: Project, task: Task, source_material: Optional[str] = None) -> JuniorOutput:
        prompt = self._render(
            {
                "agenda": project.agenda,
                "purpose": project.purpose or "",
                "assignee": task.assignee,
                "task_scope": task.task_scope,
                "source_material": source_material or "",
            }
        )
        data = self._call_json(project, prompt, max_tokens=1200)

        sources = [Source(**s) for s in data.get("sources", []) if s.get("title")]
        packet = SummaryPacket(
            role=data.get("assignee", task.assignee),
            task=data.get("task", task.task_scope),
            key_findings=data.get("key_findings", []),
            sources=sources,
            uncertain_points=data.get("uncertain_points", []),
            recommended_next_action=data.get("recommended_next_action"),
        )

        return JuniorOutput(
            output_id=f"out_{uuid.uuid4().hex[:8]}",
            project_id=project.project_id,
            task_id=task.task_id,
            assignee=task.assignee,
            task_scope=task.task_scope,
            content=data.get("content", ""),
            summary_packet=packet,
            sources=sources,
            uncertain_points=data.get("uncertain_points", []),
        )
