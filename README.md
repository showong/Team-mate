# Team-mate

Team-mate는 여러 LLM을 하나의 AI 가상부서처럼 구성해, 사용자의 아젠다를
조사 → 검토 → 품질검수 → 재작업 → 최종 보고하는 멀티 LLM 리서치 시스템입니다.

PHASE 1은 외부 워크플로우 툴(n8n 등) 없이 **코드 기반 Workflow Orchestrator**
하나로 위 업무 루프를 끝까지 돌리는 것을 목표로 합니다.

## Features

- 역할 기반 LLM 협업 (주임 / 대리 / 부팀장)
- 코드 기반 Workflow Orchestrator
- 상태머신(State Machine) 기반 업무 흐름 제어
- Decision Engine 으로 승인 / 조건부 승인 / 반려 판단
- 부분 재작업(Partial Retry) 및 Retry Manager
- Circuit Breaker 로 무한 루프 / 비용 폭증 차단
- Token & Cost Tracking
- 중간 산출물 / 검수 결과 / 로그 저장
- Mock LLM Client 로 비용 없이 전체 흐름 테스트 가능

## Architecture

```
사용자 요청
   ↓
API Layer
   ↓
Workflow Orchestrator
   ↓
Role Agents (Agenda Router → Task Splitter → Junior → Deputy → Sub-leader)
   ↓
Decision Engine ─→ Retry Manager ─→ Circuit Breaker
   ↓
Storage Layer
   ↓
Final Report
```

자세한 내용은 [`docs/architecture.md`](docs/architecture.md) 참조.

## Quick Start

```bash
# 1. 클론
git clone https://github.com/showong/team-mate.git
cd team-mate

# 2. 환경 변수
cp .env.example .env

# 3. 의존성 설치 (Python 3.11+ 권장)
pip install -r requirements.txt

# 4. API 서버 실행
uvicorn app.main:app --reload

# 5. 프로젝트 생성
curl -X POST http://localhost:8000/projects \
  -H "Content-Type: application/json" \
  -d @examples/sample_agenda.json

# 6. 워크플로우 실행
curl -X POST http://localhost:8000/projects/{project_id}/run
```

기본값은 **Mock LLM Client** 이므로 API Key 없이 전체 루프를 실행해볼 수 있습니다.
실제 LLM을 쓰려면 `.env` 의 `LLM_PROVIDER` 와 키 값을 설정하세요.

## Project Structure

```
team-mate/
├── docs/                 # 비즈니스 / 아키텍처 / 워크플로우 문서
├── app/
│   ├── api/              # FastAPI 라우트
│   ├── core/             # Orchestrator, State Machine, Decision Engine 등
│   ├── agents/           # 역할별 Agent (주임/대리/부팀장)
│   ├── llm/              # LLM Client 추상화 (Mock / OpenAI / Anthropic / Gemini)
│   ├── prompts/          # 역할별 프롬프트 템플릿 (.txt)
│   ├── schemas/          # Pydantic 데이터 모델
│   ├── services/         # 보조 서비스 (자료수집 / 보고서 / 로그 / 평가)
│   ├── storage/          # DB 추상화 + 마이그레이션
│   └── utils/            # 토큰 카운터 / 텍스트 정리 / 로거
├── tests/                # 오케스트레이터 / 상태머신 / 결정 엔진 등 테스트
└── examples/             # 샘플 입력·출력
```

## Roadmap

- **PHASE 1** — Research Team MVP (현재)
- PHASE 2 — 모델 성과 기반 역할 자동 조정
- PHASE 3 — 아이디어 미팅 / 자유토론
- PHASE 4 — 멀티 부서화 (전략기획/콘텐츠/리스크/보고서팀)

## License

MIT
