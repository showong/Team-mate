# Architecture

## 레이어 다이어그램

```
사용자 요청
   ↓
API Layer (FastAPI)
   ↓
Workflow Orchestrator
   ↓
Role Agents
   ↓
Decision Engine
   ↓
Storage / Database
   ↓
Final Report
```

## 핵심 모듈

| 모듈 | 위치 | 역할 |
| --- | --- | --- |
| API Layer | `app/api/` | 사용자 요청 접수 |
| Workflow Orchestrator | `app/core/orchestrator.py` | 전체 업무 흐름 제어 |
| State Machine | `app/core/state_machine.py` | 프로젝트 상태 전환 검증 |
| Decision Engine | `app/core/decision_engine.py` | 승인 / 조건부 / 반려 판단 |
| Retry Manager | `app/core/retry_manager.py` | 부분 재작업 제어 |
| Circuit Breaker | `app/core/circuit_breaker.py` | 무한 루프 / 비용 폭증 차단 |
| Cost Tracker | `app/core/cost_tracker.py` | 토큰 / 비용 기록 |
| Agenda Router | `app/agents/agenda_router.py` | 난이도 / 검증 강도 판단 |
| Task Splitter | `app/agents/task_splitter.py` | 주임별 업무 분해 |
| Junior Agent | `app/agents/junior_agent.py` | 조사 |
| Deputy Agent | `app/agents/deputy_agent.py` | 검토 / 통합 / 초안 |
| Sub-leader Agent | `app/agents/subleader_agent.py` | 품질검수 |
| LLM Clients | `app/llm/` | 모델 호출 추상화 (Mock/OpenAI/Anthropic/Gemini) |
| Storage | `app/storage/` | DB 추상화, Repository |
| Services | `app/services/` | 보고서 / 로그 / 평가 등 보조 |

## 토큰 다이어트

다음 단계로 **전체 응답 전체**를 넘기지 않는다. 대신 정해진 패킷만 전달한다.

### Summary Packet (주임 → 대리)

```json
{
  "role": "junior_a",
  "task": "시장 현황 조사",
  "key_findings": ["...", "..."],
  "sources": [{"title": "...", "url": "...", "summary": "..."}],
  "uncertain_points": ["..."],
  "recommended_next_action": "..."
}
```

### Review Package (대리 → 부팀장)

```json
{
  "draft_report": "...",
  "key_claims": [{"claim": "...", "evidence": "...", "source": "...", "confidence": "medium"}],
  "excluded_items": [{"item": "...", "reason": "..."}],
  "risk_points": ["..."]
}
```

## 상태머신

```
CREATED → ROUTING → TASK_SPLITTING → COLLECTING_SOURCES → RESEARCHING
       → SUMMARIZING → REVIEWING → QUALITY_CHECKING
       → (FINALIZING | RETRYING | USER_INTERVENTION_REQUIRED)
RETRYING → REVIEWING | QUALITY_CHECKING
FINALIZING → COMPLETED
* → FAILED
```

## Decision Rule

| 부팀장 결과 | 다음 행동 |
| --- | --- |
| 승인 | 최종 보고서 생성 |
| 조건부 승인 | 대리 수정 후 최종 보고서 생성 |
| 반려 (retry < max) | 부분 재작업 |
| 반려 (retry ≥ max) | Circuit Breaker → 한계 포함 보고서 생성 |

## 비용 모드

| 모드 | 주임 | 대리 | 부팀장 | 재작업 |
| --- | --- | --- | --- | --- |
| 저비용 | 1~2명 | 중간 모델 | 간단 검수 | 0~1회 |
| 균형 (default) | 2~3명 | 중상급 | 고성능 | 1회 |
| 고품질 | 3명 | 고성능 | 최고 검수 | 2회 |
