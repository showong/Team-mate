# API Spec (PHASE 1)

Base URL: `http://localhost:8000`

## POST /projects

새 프로젝트(=한 건의 리서치 업무)를 생성한다.

**Request**

```json
{
  "agenda": "중국 AI 트레이너 시장의 역할, 직무, 필요역량을 조사해줘.",
  "purpose": "커리어 확장 가능성 판단",
  "conditions": "금융 분야에 조금 더 가중치",
  "cost_mode": "balanced",
  "verification_level": "standard",
  "output_length": "normal"
}
```

**Response**

```json
{ "project_id": "tm_001", "status": "CREATED" }
```

## POST /projects/{project_id}/run

워크플로우를 실행한다. PHASE 1 에서는 동기 실행이며, 완료까지 응답을 보류한다.
(향후 비동기 큐 도입 예정.)

**Response**

```json
{
  "project_id": "tm_001",
  "status": "COMPLETED",
  "report_path": "/projects/tm_001/report"
}
```

## GET /projects/{project_id}

현재 상태와 진행 단계를 조회한다.

```json
{
  "project_id": "tm_001",
  "status": "QUALITY_CHECKING",
  "current_step": "부팀장 품질검수 중",
  "retry_count": 0,
  "estimated_cost": 980
}
```

## GET /projects/{project_id}/report

최종 보고서(또는 한계가 명시된 보고서)를 조회한다.

## GET /projects/{project_id}/logs

중간 산출물 / 검수 결과 / 상태 전환 이력을 조회한다.

## GET /projects/{project_id}/costs

호출별 토큰 / 예상 비용 누계를 조회한다.

## GET /health

헬스 체크. `{ "status": "ok" }` 반환.
