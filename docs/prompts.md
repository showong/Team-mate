# Prompts

프롬프트는 코드에 직접 박지 않고 `app/prompts/*.txt` 로 관리한다.
모델 / 역할별 분리, A/B 테스트, 버전 관리에 유리하다.

| 파일 | 역할 |
| --- | --- |
| `agenda_router.txt` | 아젠다의 난이도, 검증 강도, 추천 비용 모드 판단 |
| `task_splitter.txt` | 주임별 담당 영역 분해 |
| `junior_research.txt` | 주임의 1차 조사 |
| `deputy_review.txt` | 대리의 검토 / 통합 / 초안 작성 |
| `subleader_quality_check.txt` | 부팀장의 품질검수 |

## 공통 규칙

- 모든 프롬프트는 **JSON 응답**을 강제한다.
- 출처가 없는 단정은 금지하고 `uncertain_points` 에 분류한다.
- 모델 간 전달은 항상 `Summary Packet` 또는 `Review Package` 형태로 한다.
- 응답 길이 상한을 명시한다 (PHASE 1 기본 600~1200 tokens).

## 변수 치환

각 프롬프트는 `{{var}}` 형태의 플레이스홀더를 사용한다.
`app/utils/text_cleaner.py` 의 `render_prompt(template, vars)` 가 단순 문자열
치환을 담당한다 (Jinja 의존성 회피).

## 프롬프트 변경 시 체크리스트

1. 응답 JSON 스키마가 `app/schemas/` 와 일치하는지
2. 출력 길이 상한이 비용 모드와 충돌하지 않는지
3. Mock LLM 응답도 함께 갱신되었는지 (`app/llm/mock_client.py`)
4. 관련 테스트가 통과하는지 (`tests/`)
