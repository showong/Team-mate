"""Sub-leader Agent — final QA gate."""

from __future__ import annotations

import json
import uuid
from typing import List

from app.agents.base_agent import BaseAgent
from app.schemas import DeputyOutput, Project, Review
from app.schemas.review import (
    Decision,
    RetryTarget,
    RetryTargetRole,
    ReviewScores,
)


class SubleaderAgent(BaseAgent):
    prompt_file = "subleader_quality_check.txt"
    step_name = "subleader_qa"
    model_setting = "llm_model_subleader"

    def run(self, project: Project, deputy_output: DeputyOutput) -> Review:
        prompt = self._render(
            {
                "agenda": project.agenda,
                "purpose": project.purpose or "",
                "verification_level": project.verification_level.value,
                "review_package": json.dumps(
                    deputy_output.review_package.model_dump(), ensure_ascii=False
                ),
            }
        )
        data = self._call_json(project, prompt, max_tokens=600)

        scores = ReviewScores(**data["scores"])
        retry_targets: List[RetryTarget] = []
        for raw in data.get("retry_targets") or []:
            try:
                retry_targets.append(
                    RetryTarget(
                        role=RetryTargetRole(raw["role"]),
                        assignee=raw.get("assignee"),
                        reason=raw.get("reason", ""),
                    )
                )
            except (KeyError, ValueError):
                # Be forgiving with malformed retry targets — drop instead of crash.
                continue

        return Review(
            review_id=f"review_{uuid.uuid4().hex[:8]}",
            project_id=project.project_id,
            scores=scores,
            decision=Decision(data.get("decision", "APPROVED")),
            feedback=data.get("feedback", ""),
            retry_targets=retry_targets,
            rejection_reason_code=data.get("rejection_reason_code"),
        )
