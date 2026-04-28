"""Deputy Agent — synthesises juniors' summary packets into a draft + review package."""

from __future__ import annotations

import json
import uuid
from typing import List, Optional

from app.agents.base_agent import BaseAgent
from app.schemas import DeputyOutput, JuniorOutput, Project, Review
from app.schemas.output import ExcludedItem, KeyClaim, ReviewPackage


class DeputyAgent(BaseAgent):
    prompt_file = "deputy_review.txt"
    step_name = "deputy_review"
    model_setting = "llm_model_deputy"

    def run(
        self,
        project: Project,
        junior_outputs: List[JuniorOutput],
        previous_review: Optional[Review] = None,
    ) -> DeputyOutput:
        # Token diet: pass only the summary packets, not the juniors' full notes.
        packets = [j.summary_packet.model_dump() for j in junior_outputs]
        previous_feedback = previous_review.feedback if previous_review else ""

        prompt = self._render(
            {
                "agenda": project.agenda,
                "purpose": project.purpose or "",
                "conditions": project.conditions or "",
                "summary_packets": json.dumps(packets, ensure_ascii=False),
                "previous_feedback": previous_feedback,
            }
        )
        data = self._call_json(project, prompt, max_tokens=2000)

        key_claims = [KeyClaim(**c) for c in data.get("key_claims", []) if c.get("claim")]
        excluded = [
            ExcludedItem(**e)
            for e in data.get("excluded_items", [])
            if e.get("item")
        ]

        review_package = ReviewPackage(
            draft_report=data.get("draft_report", ""),
            key_claims=key_claims,
            excluded_items=excluded,
            risk_points=data.get("risk_points", []),
        )

        return DeputyOutput(
            output_id=f"out_{uuid.uuid4().hex[:8]}",
            project_id=project.project_id,
            task_id=f"deputy_{uuid.uuid4().hex[:8]}",
            draft_report=review_package.draft_report,
            review_package=review_package,
            junior_attribution=data.get("junior_attribution", {}),
            excluded_items=excluded,
            follow_up_questions=data.get("follow_up_questions", []),
        )
