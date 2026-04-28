"""Agenda Router — decides difficulty / verification / cost mode."""

from __future__ import annotations

from dataclasses import dataclass

from app.agents.base_agent import BaseAgent
from app.schemas import Project


@dataclass
class RoutingDecision:
    difficulty: str
    needs_search: bool
    verification_strength: str
    recommended_cost_mode: str
    junior_count: int
    rationale: str


class AgendaRouter(BaseAgent):
    prompt_file = "agenda_router.txt"
    step_name = "agenda_routing"
    model_setting = "llm_model_router"

    def run(self, project: Project) -> RoutingDecision:
        prompt = self._render(
            {
                "agenda": project.agenda,
                "purpose": project.purpose or "",
                "conditions": project.conditions or "",
                "cost_mode": project.cost_mode.value,
                "verification_level": project.verification_level.value,
            }
        )
        data = self._call_json(project, prompt, max_tokens=400)

        return RoutingDecision(
            difficulty=data.get("difficulty", "medium"),
            needs_search=bool(data.get("needs_search", True)),
            verification_strength=data.get("verification_strength", "standard"),
            recommended_cost_mode=data.get("recommended_cost_mode", "balanced"),
            junior_count=int(data.get("junior_count", 3)),
            rationale=data.get("rationale", ""),
        )
