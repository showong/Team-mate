"""Hard stops to prevent runaway retry loops or budget blow-ups."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from app.schemas import Project, Review


@dataclass
class CircuitBreakerVerdict:
    tripped: bool
    reason: Optional[str] = None


def evaluate(
    project: Project,
    review_history: List[Review],
    *,
    next_call_estimated_cost: float = 0.0,
    consecutive_failures: int = 0,
) -> CircuitBreakerVerdict:
    """Return whether the breaker should trip *before* the next retry.

    Conditions (matching the spec):
      1. retry_count >= max_retry
      2. estimated_cost (+ next call) >= budget_cap
      3. same rejection_reason_code repeated
      4. repeated raw model failures
    """

    if project.retry_count >= project.max_retry:
        return CircuitBreakerVerdict(True, "max_retry 초과")

    if project.estimated_cost + next_call_estimated_cost >= project.budget_cap:
        return CircuitBreakerVerdict(True, "budget_cap 초과 위험")

    rejection_codes = [r.rejection_reason_code for r in review_history if r.rejection_reason_code]
    if len(rejection_codes) >= 2 and rejection_codes[-1] == rejection_codes[-2]:
        return CircuitBreakerVerdict(True, f"동일 반려 사유 반복: {rejection_codes[-1]}")

    if consecutive_failures >= 3:
        return CircuitBreakerVerdict(True, "모델 호출 반복 실패")

    return CircuitBreakerVerdict(False)
