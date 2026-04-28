"""Deterministic mock LLM client.

Used as the default in PHASE 1 so the entire orchestration loop can run end
to end without burning a single real API call. Each role gets a hand-crafted
JSON response that already conforms to the schema the corresponding agent
expects.

The client also exposes hooks (`force_decision`, `force_failure`) so tests can
simulate retry / circuit-breaker scenarios deterministically.
"""

from __future__ import annotations

import json
import re
from typing import List, Optional

from app.llm.base_client import BaseLLMClient, LLMResponse
from app.utils.token_counter import estimate_cost


class MockLLMClient(BaseLLMClient):
    name = "mock"

    def __init__(
        self,
        *,
        force_decision: Optional[str] = None,
        force_failure_steps: Optional[List[str]] = None,
    ) -> None:
        # Allows tests to coerce the sub-leader into REJECTED, etc.
        self.force_decision = force_decision
        self.force_failure_steps = force_failure_steps or []
        self._call_log: List[dict] = []

    def complete(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        max_tokens: int = 1200,
        temperature: float = 0.2,
    ) -> LLMResponse:
        role = self._infer_role(prompt)
        if role in self.force_failure_steps:
            raise RuntimeError(f"Mock failure injected for role={role}")

        text = self._respond_for(role, prompt)
        cost = estimate_cost(model or "mock", prompt, text)

        self._call_log.append({"role": role, "model": model, "tokens_out": cost.output_tokens})

        return LLMResponse(
            text=text,
            model_name=model or "mock",
            input_tokens=cost.input_tokens,
            output_tokens=cost.output_tokens,
            estimated_cost=cost.estimated_cost,
        )

    # ----- helpers -----------------------------------------------------

    @staticmethod
    def _infer_role(prompt: str) -> str:
        head = prompt[:400]
        if "ROLE: AGENDA_ROUTER" in head:
            return "router"
        if "ROLE: TASK_SPLITTER" in head:
            return "splitter"
        if "ROLE: JUNIOR_RESEARCHER" in head:
            return "junior"
        if "ROLE: DEPUTY_REVIEWER" in head:
            return "deputy"
        if "ROLE: SUBLEADER_QA" in head:
            return "subleader"
        return "unknown"

    def _respond_for(self, role: str, prompt: str) -> str:
        if role == "router":
            return json.dumps(
                {
                    "difficulty": "medium",
                    "needs_search": True,
                    "verification_strength": "standard",
                    "recommended_cost_mode": "balanced",
                    "junior_count": 3,
                    "rationale": "주제는 다층적이며 시장/직무/사례 측면 분리가 효과적임.",
                },
                ensure_ascii=False,
            )

        if role == "splitter":
            return json.dumps(
                {
                    "tasks": [
                        {
                            "assignee": "junior_a",
                            "task_scope": "시장 현황과 성장 배경 조사",
                        },
                        {
                            "assignee": "junior_b",
                            "task_scope": "주요 직무와 필요 역량 조사",
                        },
                        {
                            "assignee": "junior_c",
                            "task_scope": "사례 및 적용 가능성 조사",
                        },
                    ]
                },
                ensure_ascii=False,
            )

        if role == "junior":
            assignee = self._extract_var(prompt, "assignee") or "junior_x"
            scope = self._extract_var(prompt, "task_scope") or "지정 영역 조사"
            return json.dumps(
                {
                    "assignee": assignee,
                    "task": scope,
                    "content": (
                        f"[{assignee}] {scope}에 대한 1차 조사 결과입니다. "
                        "핵심 발견과 출처를 정리했습니다."
                    ),
                    "key_findings": [
                        f"{scope} 관련 핵심 발견 1",
                        f"{scope} 관련 핵심 발견 2",
                        f"{scope} 관련 핵심 발견 3",
                    ],
                    "sources": [
                        {
                            "title": f"{scope} 보고서 (Mock)",
                            "url": "https://example.com/mock",
                            "summary": "신뢰성 중상 등급의 모의 출처.",
                        }
                    ],
                    "uncertain_points": [f"{scope} 관련 수치는 출처 보강 필요"],
                    "recommended_next_action": "대리 단계에서 출처 보강 요청",
                },
                ensure_ascii=False,
            )

        if role == "deputy":
            return json.dumps(
                {
                    "draft_report": (
                        "# 리서치 보고서 (초안)\n\n"
                        "## 1. 요약\n주임 3인의 결과를 통합한 초안입니다.\n\n"
                        "## 2. 주요 발견\n- 시장 현황\n- 직무·역량\n- 적용 사례\n\n"
                        "## 3. 한계\n- 일부 수치 출처 보강 필요"
                    ),
                    "key_claims": [
                        {
                            "claim": "해당 시장은 빠르게 확장 중이다",
                            "evidence": "주임 A 조사 요약",
                            "source": "Mock 시장 보고서",
                            "confidence": "medium",
                        }
                    ],
                    "excluded_items": [
                        {"item": "근거 부족한 추정 수치", "reason": "1차 출처 부재"}
                    ],
                    "risk_points": ["금융권 사례 부족", "최신 통계 출처 보강 필요"],
                    "junior_attribution": {
                        "junior_a": "시장 현황 섹션 반영",
                        "junior_b": "직무·역량 섹션 반영",
                        "junior_c": "사례 섹션 반영",
                    },
                    "follow_up_questions": ["금융권 도입 사례 추가 확보 가능 여부"],
                },
                ensure_ascii=False,
            )

        if role == "subleader":
            decision = self.force_decision or "APPROVED"
            scores = {
                "APPROVED": (5, 4, 5, 4, 5),
                "CONDITIONAL_APPROVED": (4, 4, 4, 4, 4),
                "REJECTED": (3, 2, 3, 3, 2),
            }.get(decision, (5, 4, 5, 4, 5))
            payload = {
                "scores": {
                    "accuracy": scores[0],
                    "source_quality": scores[1],
                    "logic": scores[2],
                    "completeness": scores[3],
                    "hallucination_risk": scores[4],
                },
                "decision": decision,
                "feedback": (
                    "전반적으로 구조는 양호. 일부 수치 출처 보강 권고."
                    if decision != "REJECTED"
                    else "출처 부족 및 핵심 주장 근거 미흡."
                ),
                "rejection_reason_code": None if decision != "REJECTED" else "INSUFFICIENT_SOURCES",
                "retry_targets": (
                    [{"role": "junior", "assignee": "junior_a", "reason": "시장 통계 출처 보강"}]
                    if decision == "REJECTED"
                    else []
                ),
            }
            return json.dumps(payload, ensure_ascii=False)

        # Fallback echo
        return json.dumps({"echo": prompt[:200]}, ensure_ascii=False)

    @staticmethod
    def _extract_var(prompt: str, key: str) -> Optional[str]:
        match = re.search(rf"^{key}:\s*(.+)$", prompt, re.MULTILINE)
        return match.group(1).strip() if match else None
