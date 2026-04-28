"""Team-mate Phase 1 — Streamlit UI

Orchestrator를 직접 임포트해서 HTTP 서버 없이 실행합니다.
실행: streamlit run streamlit_app.py
"""

from __future__ import annotations

import time
from typing import Optional

import streamlit as st

# ── 페이지 설정 ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Team-mate",
    page_icon="🤝",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 임포트 (Streamlit 페이지 설정 이후) ─────────────────────────────────────
from app.core.orchestrator import Orchestrator
from app.llm.mock_client import MockLLMClient
from app.schemas.project import CostMode, VerificationLevel, OutputLength
from app.schemas import ProjectCreate
from app.storage.database import get_repositories, reset_repositories
from app.services.log_service import LogService
from app.services.report_service import ReportService


# ── 세션 상태 초기화 ─────────────────────────────────────────────────────────
def _init_state() -> None:
    defaults = {
        "result": None,
        "project_id": None,
        "running": False,
        "error": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


_init_state()


# ── 사이드바 — 설정 ──────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ 설정")

    cost_mode = st.selectbox(
        "비용 모드",
        options=[m.value for m in CostMode],
        index=1,  # balanced
        help="저비용: 주임 1~2명 / 균형: 2~3명 / 고품질: 3명 + 고성능 검수",
    )

    verification_level = st.selectbox(
        "검증 강도",
        options=[v.value for v in VerificationLevel],
        index=1,  # standard
    )

    output_length = st.selectbox(
        "보고서 길이",
        options=[o.value for o in OutputLength],
        index=1,  # normal
    )

    st.divider()
    st.caption("LLM 설정")

    provider = st.selectbox(
        "LLM Provider",
        ["mock", "openai", "anthropic", "gemini", "local"],
        index=0,
        help="mock = API Key 없이 실행 (테스트용)",
    )

    if provider != "mock":
        api_key = st.text_input(
            f"{provider.upper()} API Key",
            type="password",
            placeholder="sk-...",
        )
    else:
        api_key = ""
        st.info("Mock 모드: API Key 불필요", icon="🤖")

    st.divider()
    if st.button("🗑️ 세션 초기화", use_container_width=True):
        reset_repositories()
        for k in ["result", "project_id", "running", "error"]:
            st.session_state[k] = None if k != "running" else False
        st.rerun()


# ── 헤더 ─────────────────────────────────────────────────────────────────────
st.title("🤝 Team-mate")
st.caption("AI 가상부서 — 주임 조사 → 대리 검토 → 부팀장 품질검수 → 최종 보고")

st.divider()

# ── 입력 폼 ──────────────────────────────────────────────────────────────────
with st.form("agenda_form"):
    agenda = st.text_area(
        "📋 아젠다 (조사 주제)",
        placeholder="예) 중국 AI 트레이너 시장의 역할, 직무, 필요역량을 조사해줘.",
        height=100,
    )
    col1, col2 = st.columns(2)
    with col1:
        purpose = st.text_input(
            "🎯 목적",
            placeholder="예) 커리어 확장 가능성 판단",
        )
    with col2:
        conditions = st.text_input(
            "📌 조건 / 가중치",
            placeholder="예) 금융 분야에 조금 더 가중치",
        )

    submitted = st.form_submit_button("🚀 Team-mate 실행", use_container_width=True, type="primary")


# ── 실행 ─────────────────────────────────────────────────────────────────────
if submitted:
    if not agenda.strip():
        st.warning("아젠다를 입력해주세요.")
        st.stop()

    st.session_state.result = None
    st.session_state.error = None
    st.session_state.running = True

    payload = ProjectCreate(
        agenda=agenda.strip(),
        purpose=purpose.strip() or None,
        conditions=conditions.strip() or None,
        cost_mode=CostMode(cost_mode),
        verification_level=VerificationLevel(verification_level),
        output_length=OutputLength(output_length),
    )

    # LLM 클라이언트 선택
    if provider == "mock":
        llm = MockLLMClient()
    else:
        import importlib
        try:
            import os
            os.environ[f"{provider.upper()}_API_KEY"] = api_key
            from app.config import Settings
            from app.llm.factory import build_llm_client
            settings = Settings(**{f"{provider}_api_key": api_key, "llm_provider": provider})
            llm = build_llm_client(settings)
        except Exception as e:
            st.error(f"LLM 클라이언트 초기화 실패: {e}")
            st.stop()

    repos = get_repositories()
    orch = Orchestrator(repos=repos, llm=llm)

    # 단계별 진행 상황 표시
    with st.status("Team-mate 업무 진행 중...", expanded=True) as status:
        try:
            st.write("📂 프로젝트 생성 중...")
            project = orch.create_project(payload)
            st.session_state.project_id = project.project_id
            st.write(f"✅ 프로젝트 생성 완료 (`{project.project_id}`)")

            st.write("🧭 아젠다 분석 중 (Agenda Router)...")
            time.sleep(0.2)

            st.write("📝 업무 분해 중 (Task Splitter)...")
            time.sleep(0.2)

            st.write("🔍 주임 조사 중...")
            time.sleep(0.3)

            st.write("📊 대리 검토 및 통합 중...")
            time.sleep(0.2)

            st.write("🔎 부팀장 품질검수 중...")
            time.sleep(0.2)

            result = orch.run_project(project.project_id)
            st.session_state.result = result

            if result.project.status.value == "COMPLETED":
                label = "✅ 완료!" if not (result.report and result.report.is_partial) else "⚠️ 완료 (한계 포함)"
                status.update(label=label, state="complete", expanded=False)
            else:
                status.update(label="❌ 실패", state="error", expanded=True)

        except Exception as exc:
            st.session_state.error = str(exc)
            status.update(label=f"❌ 오류: {exc}", state="error")

    st.session_state.running = False


# ── 결과 표시 ─────────────────────────────────────────────────────────────────
result = st.session_state.get("result")
error = st.session_state.get("error")

if error:
    st.error(f"실행 오류: {error}")

if result is not None:
    project = result.project
    repos = get_repositories()

    # 핵심 지표 요약
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("상태", project.status.value)
    with col2:
        final_score = (
            round(result.review.scores.average, 2) if result.review else "-"
        )
        st.metric("최종 품질 점수", f"{final_score} / 5.0")
    with col3:
        st.metric("재작업 횟수", project.retry_count)
    with col4:
        st.metric("예상 비용", f"{project.estimated_cost:.4f}")

    st.divider()

    # 탭 구성
    tab_report, tab_review, tab_logs, tab_costs = st.tabs(
        ["📄 최종 보고서", "🔎 검수 결과", "📋 워크플로우 로그", "💰 비용 분석"]
    )

    # ── 탭 1: 보고서 ─────────────────────────────────────────────────────────
    with tab_report:
        if result.report:
            if result.report.is_partial:
                st.warning("Circuit Breaker 작동으로 인해 한계가 포함된 보고서입니다.")
            st.markdown(result.report.markdown)

            st.download_button(
                label="📥 보고서 다운로드 (.md)",
                data=result.report.markdown,
                file_name=f"report_{project.project_id}.md",
                mime="text/markdown",
            )
        else:
            st.info("보고서가 생성되지 않았습니다.")

    # ── 탭 2: 검수 결과 ──────────────────────────────────────────────────────
    with tab_review:
        if result.review:
            review = result.review
            decision_color = {
                "APPROVED": "green",
                "CONDITIONAL_APPROVED": "orange",
                "REJECTED": "red",
            }.get(review.decision.value, "gray")

            st.markdown(
                f"### 판정: :{decision_color}[{review.decision.value}]"
            )
            st.write(f"**피드백:** {review.feedback}")

            st.markdown("#### 세부 점수")
            scores = review.scores
            score_data = {
                "항목": ["사실성", "출처 품질", "논리성", "완성도", "할루시네이션 안전도"],
                "점수": [
                    scores.accuracy,
                    scores.source_quality,
                    scores.logic,
                    scores.completeness,
                    scores.hallucination_risk,
                ],
            }
            import pandas as pd
            st.dataframe(
                pd.DataFrame(score_data),
                use_container_width=True,
                hide_index=True,
            )
            st.metric("평균 점수", f"{scores.average:.2f} / 5.0")

            if review.retry_targets:
                st.markdown("#### 재작업 지시")
                for t in review.retry_targets:
                    st.write(f"- `{t.role.value}` ({t.assignee or '-'}): {t.reason}")
        else:
            st.info("검수 결과 없음.")

    # ── 탭 3: 워크플로우 로그 ────────────────────────────────────────────────
    with tab_logs:
        log_svc = LogService(repos)
        log = log_svc.collect(project.project_id)

        # 라우팅 결과
        if result.routing:
            r = result.routing
            st.markdown("#### 🧭 Agenda Router 결과")
            col1, col2, col3 = st.columns(3)
            col1.metric("난이도", r.difficulty)
            col2.metric("주임 수", r.junior_count)
            col3.metric("검증 강도", r.verification_strength)
            st.caption(f"판단 근거: {r.rationale}")
            st.divider()

        # 주임 산출물
        if log.junior_outputs:
            st.markdown("#### 🔍 주임 조사 결과")
            for jo in log.junior_outputs:
                with st.expander(f"`{jo.assignee}` — {jo.task_scope}"):
                    pkt = jo.summary_packet
                    st.markdown("**핵심 발견**")
                    for f in pkt.key_findings:
                        st.write(f"- {f}")
                    if pkt.sources:
                        st.markdown("**출처**")
                        for s in pkt.sources:
                            link = f"[{s.title}]({s.url})" if s.url else s.title
                            st.write(f"- {link}: {s.summary or ''}")
                    if pkt.uncertain_points:
                        st.markdown("**불확실한 내용**")
                        for u in pkt.uncertain_points:
                            st.write(f"- ⚠️ {u}")
            st.divider()

        # 대리 산출물
        if log.deputy_outputs:
            st.markdown("#### 📊 대리 검토 결과")
            latest_deputy = log.deputy_outputs[-1]
            if latest_deputy.review_package.risk_points:
                st.markdown("**리스크 포인트**")
                for rp in latest_deputy.review_package.risk_points:
                    st.write(f"- ⚠️ {rp}")
            if latest_deputy.excluded_items:
                st.markdown("**제외된 내용**")
                for ex in latest_deputy.excluded_items:
                    st.write(f"- `{ex.item}` — {ex.reason}")
            if latest_deputy.follow_up_questions:
                st.markdown("**추가 확인 필요**")
                for q in latest_deputy.follow_up_questions:
                    st.write(f"- {q}")

    # ── 탭 4: 비용 분석 ──────────────────────────────────────────────────────
    with tab_costs:
        costs = repos.costs.list_for_project(project.project_id)
        if costs:
            import pandas as pd

            df = pd.DataFrame([
                {
                    "단계": c.step,
                    "모델": c.model_name,
                    "입력 토큰": c.input_tokens,
                    "출력 토큰": c.output_tokens,
                    "비용": c.estimated_cost,
                }
                for c in costs
            ])
            st.dataframe(df, use_container_width=True, hide_index=True)

            total = sum(c.estimated_cost for c in costs)
            col1, col2, col3 = st.columns(3)
            col1.metric("총 예상 비용", f"{total:.4f}")
            col2.metric("총 LLM 호출 수", len(costs))
            col3.metric(
                "총 토큰",
                f"{sum(c.input_tokens + c.output_tokens for c in costs):,}",
            )

            st.bar_chart(df.set_index("단계")["비용"])
        else:
            st.info("비용 기록 없음.")
