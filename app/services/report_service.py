"""Final-report assembly.

Takes the deputy's draft + the latest review and emits a Markdown report.
If the circuit breaker tripped, we annotate the report with limits + an
"intervention required" note rather than fabricating completeness.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from app.schemas import DeputyOutput, JuniorOutput, Project, Review


@dataclass
class FinalReport:
    project_id: str
    markdown: str
    is_partial: bool
    limits: List[str]


class ReportService:
    def build(
        self,
        project: Project,
        deputy_output: DeputyOutput,
        review: Optional[Review],
        junior_outputs: List[JuniorOutput],
        *,
        circuit_break_reason: Optional[str] = None,
    ) -> FinalReport:
        sections: List[str] = []
        sections.append(f"# {project.agenda}\n")
        if project.purpose:
            sections.append(f"> **목적**: {project.purpose}\n")

        sections.append(deputy_output.draft_report.strip())

        if deputy_output.review_package.key_claims:
            sections.append("\n## 핵심 주장 및 근거\n")
            for c in deputy_output.review_package.key_claims:
                source = f" — _{c.source}_" if c.source else ""
                sections.append(
                    f"- **{c.claim}** ({c.confidence}){source}: {c.evidence or ''}"
                )

        if deputy_output.review_package.risk_points:
            sections.append("\n## 리스크 및 주의사항\n")
            for r in deputy_output.review_package.risk_points:
                sections.append(f"- {r}")

        sections.append("\n## 출처\n")
        seen = set()
        for j in junior_outputs:
            for s in j.sources:
                key = (s.title, s.url)
                if key in seen:
                    continue
                seen.add(key)
                line = f"- {s.title}"
                if s.url:
                    line += f" ({s.url})"
                sections.append(line)

        is_partial = circuit_break_reason is not None
        limits: List[str] = []
        if review and review.feedback:
            limits.append(review.feedback)
        if circuit_break_reason:
            limits.append(f"Circuit Breaker 작동: {circuit_break_reason}")
        if deputy_output.follow_up_questions:
            limits.extend(deputy_output.follow_up_questions)

        if limits:
            sections.append("\n## 한계 및 추가 확인 필요사항\n")
            for limit in limits:
                sections.append(f"- {limit}")
            if is_partial:
                sections.append(
                    "\n> **주의**: 위 항목은 사용자 개입이 필요할 수 있습니다."
                )

        return FinalReport(
            project_id=project.project_id,
            markdown="\n".join(sections).strip() + "\n",
            is_partial=is_partial,
            limits=limits,
        )
