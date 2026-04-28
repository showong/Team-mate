# Workflow

## 전체 프로세스

1. 사용자가 아젠다 입력
2. Agenda Router 가 업무 성격 / 난이도 / 검증 강도 판단
3. Task Splitter 가 주임별 업무 분해
4. Source Collector 가 자료 수집 (사용자 자료 우선)
5. 주임 모델들이 조사 수행
6. Summary Packet 생성
7. 대리 모델이 검토 / 통합 / 초안 작성
8. Review Package 생성
9. 부팀장 모델이 품질검수
10. Decision Engine 이 승인 / 조건부 / 반려 판단
11. 필요 시 Retry Manager 가 부분 재작업 트리거
12. Circuit Breaker 가 재시도 한도 / 비용 한도 확인
13. 최종 보고서 생성
14. 비용 / 품질 / 성과 저장
15. 사용자에게 결과 제공

## 상태 전환

| 상태 | 의미 |
| --- | --- |
| CREATED | 프로젝트 생성 |
| ROUTING | 아젠다 분석 중 |
| TASK_SPLITTING | 업무 분해 중 |
| COLLECTING_SOURCES | 자료 수집 중 |
| RESEARCHING | 주임 조사 중 |
| SUMMARIZING | 요약 패킷 생성 중 |
| REVIEWING | 대리 검토 중 |
| QUALITY_CHECKING | 부팀장 검수 중 |
| RETRYING | 재작업 중 |
| FINALIZING | 최종 보고서 생성 중 |
| COMPLETED | 완료 |
| FAILED | 실패 |
| USER_INTERVENTION_REQUIRED | 사용자 개입 필요 |

## 업무 단위 상태

PENDING / RUNNING / SUBMITTED / APPROVED / CONDITIONAL_APPROVED / REJECTED /
RETRYING / SKIPPED / FAILED

## 부분 재작업 규칙

| 반려 사유 | 재작업 대상 |
| --- | --- |
| 자료 부족 | 해당 주임 |
| 출처 누락 | 해당 주임 또는 대리 |
| 논리 구조 문제 | 대리 |
| 최종 표현 문제 | 대리 (수정만) |

## Circuit Breaker

작동 조건:

- 최대 재시도 초과
- 동일 반려 사유 반복
- 예산 한도 초과
- 모델 응답 실패 반복
- 필수 출처 확보 실패

작동 후:

- 현재까지 확보된 내용으로 보고서 생성
- 한계 / 미확인 사항 명시
- 사용자 개입 필요 여부 표시
- 실패 사유와 비용 기록
