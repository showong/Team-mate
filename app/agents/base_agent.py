"""Shared agent plumbing: prompt loading + JSON-only LLM round-trip."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Optional

from app.config import Settings, get_settings
from app.core.cost_tracker import CostTracker
from app.llm.base_client import BaseLLMClient, LLMResponse
from app.schemas import Project
from app.utils.text_cleaner import extract_json, render_prompt


PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


class BaseAgent:
    """Common behaviour: render a prompt, call the LLM, parse JSON, log cost."""

    prompt_file: str = ""
    step_name: str = ""

    def __init__(
        self,
        llm: BaseLLMClient,
        cost_tracker: CostTracker,
        settings: Optional[Settings] = None,
        *,
        model_override: Optional[str] = None,
    ) -> None:
        self._llm = llm
        self._cost = cost_tracker
        self._settings = settings or get_settings()
        self._model_override = model_override

    # ----- prompt -----

    def _load_prompt(self) -> str:
        return (PROMPTS_DIR / self.prompt_file).read_text(encoding="utf-8")

    def _render(self, variables: Mapping[str, Any]) -> str:
        return render_prompt(self._load_prompt(), variables)

    # ----- llm call -----

    def _model_for_role(self) -> str:
        # 인스턴스 단위 override가 우선
        if self._model_override:
            return self._model_override
        # 그 다음 Settings 의 model_setting 필드를 읽음
        return getattr(self._settings, self.model_setting, "mid")

    model_setting: str = "llm_model_deputy"

    def _call(self, project: Project, prompt: str, *, max_tokens: int = 1200) -> LLMResponse:
        response = self._llm.complete(
            prompt,
            model=self._model_for_role(),
            max_tokens=max_tokens,
        )
        self._cost.record(project, self.step_name, response)
        return response

    def _call_json(self, project: Project, prompt: str, *, max_tokens: int = 1200) -> dict:
        response = self._call(project, prompt, max_tokens=max_tokens)
        return extract_json(response.text)
