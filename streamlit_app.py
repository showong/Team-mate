"""Team-mate — AI 가상 팀 미팅룸

아젠다가 입력되면 주임(조사) → 대리(크로스 피드백) → 부팀장(최종 심사)까지
모든 발언이 순서대로 펼쳐지는 가상 회의 화면.
실행: streamlit run streamlit_app.py
"""

from __future__ import annotations

import time
from typing import Optional

import streamlit as st

# ── 페이지 설정 ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Team-mate | AI 미팅룸",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 임포트 ────────────────────────────────────────────────────────────────────
from app.core.orchestrator import Orchestrator
from app.llm.mock_client import MockLLMClient
from app.schemas import ProjectCreate
from app.schemas.project import CostMode, OutputLength, VerificationLevel
from app.storage.database import get_repositories, reset_repositories

# ── 커스텀 CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* 전체 배경 */
.stApp { background-color: #0f1117; }

/* 미팅룸 헤더 */
.meeting-header {
    background: linear-gradient(135deg, #1e3a5f 0%, #0d2137 100%);
    border: 1px solid #2d5986;
    border-radius: 12px;
    padding: 20px 28px;
    margin-bottom: 24px;
}
.meeting-title { font-size: 22px; font-weight: 700; color: #e2e8f0; margin: 0; }
.meeting-sub   { font-size: 13px; color: #94a3b8; margin-top: 4px; }
.meeting-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 600;
    margin-left: 8px;
}
.badge-live    { background: #065f46; color: #6ee7b7; }
.badge-done    { background: #1e3a5f; color: #93c5fd; }
.badge-wait    { background: #374151; color: #9ca3af; }

/* 발언 카드 공통 */
.speech-card {
    border-radius: 12px;
    padding: 16px 20px;
    margin: 10px 0;
    border-left: 4px solid;
    position: relative;
}
.role-name {
    font-size: 13px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 8px;
}
.role-scope {
    font-size: 11px;
    opacity: 0.7;
    margin-left: 8px;
    font-weight: 400;
    text-transform: none;
}

/* 역할별 색상 */
.card-router   { background: #1c1f26; border-color: #6b7280; }
.card-router   .role-name { color: #9ca3af; }

.card-junior-a { background: #0d1f3c; border-color: #3b82f6; }
.card-junior-a .role-name { color: #93c5fd; }

.card-junior-b { background: #0d2626; border-color: #06b6d4; }
.card-junior-b .role-name { color: #67e8f9; }

.card-junior-c { background: #0d2318; border-color: #10b981; }
.card-junior-c .role-name { color: #6ee7b7; }

.card-deputy   { background: #261a00; border-color: #f59e0b; }
.card-deputy   .role-name { color: #fcd34d; }

.card-subleader { background: #200f0f; border-color: #ef4444; }
.card-subleader .role-name { color: #fca5a5; }

.card-report   { background: #150d2e; border-color: #8b5cf6; }
.card-report   .role-name { color: #c4b5fd; }

/* 발언 내용 */
.speech-body   { color: #cbd5e1; font-size: 14px; line-height: 1.7; }
.finding-item  { padding: 4px 0; color: #e2e8f0; }
.finding-item::before { content: "▸ "; color: #64748b; }

.uncertain-item { padding: 4px 0; color: #fbbf24; font-size: 13px; }
.uncertain-item::before { content: "⚠ "; }

.source-item   { padding: 3px 0; color: #94a3b8; font-size: 12px; }
.source-item::before { content: "🔗 "; }

.feedback-item { padding: 4px 0; color: #d1d5db; font-size: 13px; }
.feedback-item::before { content: "↳ "; color: #6b7280; }

.excluded-item { padding: 4px 0; color: #6b7280; font-size: 12px; font-style: italic; }
.excluded-item::before { content: "✕ "; color: #ef4444; }

.risk-item     { padding: 4px 0; color: #fca5a5; font-size: 13px; }
.risk-item     ::before { content: "⚡ "; }

/* 점수 배지 */
.score-grid    { display: flex; gap: 10px; flex-wrap: wrap; margin: 10px 0; }
.score-item    {
    background: #1e293b;
    border-radius: 8px;
    padding: 8px 14px;
    text-align: center;
    min-width: 80px;
}
.score-label   { font-size: 10px; color: #64748b; text-transform: uppercase; }
.score-value   { font-size: 22px; font-weight: 700; color: #e2e8f0; }

/* 판정 배너 */
.decision-approved   { background:#065f46; color:#6ee7b7; border:1px solid #059669;
                        border-radius:8px; padding:10px 20px; font-size:16px; font-weight:700; }
.decision-conditional{ background:#78350f; color:#fcd34d; border:1px solid #d97706;
                        border-radius:8px; padding:10px 20px; font-size:16px; font-weight:700; }
.decision-rejected   { background:#7f1d1d; color:#fca5a5; border:1px solid #dc2626;
                        border-radius:8px; padding:10px 20px; font-size:16px; font-weight:700; }

/* 구분선 */
.timeline-divider {
    border: none;
    border-top: 1px dashed #2d3748;
    margin: 20px 0;
}

/* 메트릭 칩 */
.metric-row { display: flex; gap: 12px; flex-wrap: wrap; margin: 12px 0; }
.metric-chip {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 20px;
    padding: 5px 14px;
    font-size: 12px;
    color: #94a3b8;
}
.metric-chip b { color: #e2e8f0; }

/* 섹션 레이블 */
.section-label {
    font-size: 11px;
    font-weight: 700;
    color: #475569;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin: 14px 0 6px;
}

/* 참여자 패널 */
.participant-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 0;
    border-bottom: 1px solid #1e293b;
    font-size: 13px;
    color: #94a3b8;
}
.participant-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
}
</style>
""", unsafe_allow_html=True)


# ── 세션 상태 초기화 ──────────────────────────────────────────────────────────
def _init_state() -> None:
    for k, v in {"result": None, "running": False, "error": None}.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()


# ── 헬퍼: HTML 카드 렌더 ──────────────────────────────────────────────────────
def _html(raw: str) -> None:
    st.markdown(raw, unsafe_allow_html=True)


def _speech_start(cls: str, role: str, scope: str = "") -> None:
    scope_html = f'<span class="role-scope">— {scope}</span>' if scope else ""
    _html(f"""
    <div class="speech-card {cls}">
      <div class="role-name">{role}{scope_html}</div>
      <div class="speech-body">
    """)


def _speech_end() -> None:
    _html("</div></div>")


def _items(tag: str, items: list, css: str) -> None:
    if not items:
        return
    _html(f'<div class="section-label">{tag}</div>')
    for item in items:
        _html(f'<div class="{css}">{item}</div>')


def _divider() -> None:
    _html('<hr class="timeline-divider">')


# ── 참여자 사이드바 ───────────────────────────────────────────────────────────
PARTICIPANTS = [
    ("#3b82f6", "👨‍💼 주임 A", "시장·배경 조사"),
    ("#06b6d4", "👨‍💼 주임 B", "직무·역량 조사"),
    ("#10b981", "👨‍💼 주임 C", "사례·적용 가능성"),
    ("#f59e0b", "👩‍💼 대리",    "검토·통합·초안"),
    ("#ef4444", "🧑‍💼 부팀장", "품질검수·최종판정"),
]

with st.sidebar:
    st.markdown("### 🏢 Team-mate")
    st.markdown("AI 가상부서 미팅룸")
    st.divider()

    st.markdown("**👥 참여 멤버**")
    for color, name, role in PARTICIPANTS:
        _html(f"""
        <div class="participant-item">
          <div class="participant-dot" style="background:{color}"></div>
          <div><b style="color:#e2e8f0">{name}</b><br>
               <span style="font-size:11px">{role}</span></div>
        </div>""")

    st.divider()
    st.markdown("**⚙️ 미팅 설정**")

    cost_mode = st.selectbox("비용 모드",
        [m.value for m in CostMode], index=1,
        help="균형 = 주임 2~3명, 고품질 = 주임 3명 + 고성능 검수")
    verification_level = st.selectbox("검증 강도",
        [v.value for v in VerificationLevel], index=1)
    output_length = st.selectbox("보고서 길이",
        [o.value for o in OutputLength], index=1)

    st.divider()
    provider = st.selectbox("LLM Provider",
        ["mock", "openai", "anthropic", "gemini", "local"], index=0)
    if provider != "mock":
        api_key = st.text_input(f"{provider.upper()} API Key",
                                type="password", placeholder="sk-...")
    else:
        api_key = ""
        st.info("Mock 모드 — API Key 불필요", icon="🤖")

    st.divider()
    if st.button("🗑️ 미팅 초기화", use_container_width=True):
        reset_repositories()
        st.session_state.result = None
        st.session_state.error = None
        st.rerun()


# ── 입력 폼 ───────────────────────────────────────────────────────────────────
_html("""
<div class="meeting-header">
  <div class="meeting-title">🏢 Team-mate 가상 팀 미팅
    <span class="meeting-badge badge-wait" id="meeting-status">대기 중</span>
  </div>
  <div class="meeting-sub">아젠다를 입력하면 주임 · 대리 · 부팀장이 순서대로 발언합니다</div>
</div>
""")

with st.form("agenda_form"):
    agenda = st.text_area("📋 아젠다 (조사 주제)",
        placeholder="예) 중국 AI 트레이너 시장의 역할, 직무, 필요역량을 조사해줘.",
        height=90)
    c1, c2 = st.columns(2)
    purpose    = c1.text_input("🎯 목적",    placeholder="예) 커리어 확장 가능성 판단")
    conditions = c2.text_input("📌 특이사항", placeholder="예) 금융 분야에 가중치")
    submitted  = st.form_submit_button("🚀 미팅 시작", use_container_width=True, type="primary")


# ── 실행 ──────────────────────────────────────────────────────────────────────
if submitted:
    if not agenda.strip():
        st.warning("아젠다를 입력해주세요.")
        st.stop()

    st.session_state.result = None
    st.session_state.error  = None

    payload = ProjectCreate(
        agenda=agenda.strip(),
        purpose=purpose.strip() or None,
        conditions=conditions.strip() or None,
        cost_mode=CostMode(cost_mode),
        verification_level=VerificationLevel(verification_level),
        output_length=OutputLength(output_length),
    )

    if provider == "mock":
        llm = MockLLMClient()
    else:
        try:
            import os
            os.environ[f"{provider.upper()}_API_KEY"] = api_key
            from app.config import Settings
            from app.llm.factory import build_llm_client
            s = Settings(**{f"{provider}_api_key": api_key, "llm_provider": provider})
            llm = build_llm_client(s)
        except Exception as e:
            st.error(f"LLM 초기화 실패: {e}")
            st.stop()

    repos = get_repositories()
    orch  = Orchestrator(repos=repos, llm=llm)

    STEPS = [
        ("🧭", "아젠다 분석 중…",    0.15),
        ("📋", "업무 분해 중…",      0.15),
        ("🔍", "주임 조사 중…",      0.30),
        ("📊", "대리 통합 중…",      0.20),
        ("🔎", "부팀장 검수 중…",    0.20),
        ("📄", "최종 보고서 생성…",  0.10),
    ]

    with st.status("🔴  미팅 진행 중", expanded=True) as status_box:
        project = orch.create_project(payload)
        for icon, label, wait in STEPS:
            st.write(f"{icon}  {label}")
            time.sleep(wait)
        result = orch.run_project(project.project_id)
        st.session_state.result = result
        label = "✅  미팅 완료" if not (result.report and result.report.is_partial) else "⚠️  미팅 완료 (한계 포함)"
        status_box.update(label=label, state="complete", expanded=False)


# ── 미팅 결과 표시 ────────────────────────────────────────────────────────────
result = st.session_state.get("result")
if result is None:
    st.stop()

project  = result.project
repos    = get_repositories()
log      = result.log
review   = result.review
routing  = result.routing

# 상단 핵심 지표
final_score = f"{review.scores.average:.1f} / 5.0" if review else "-"
decision_val = review.decision.value if review else "-"
decision_emoji = {"APPROVED": "✅", "CONDITIONAL_APPROVED": "🟡", "REJECTED": "❌"}.get(decision_val, "")

_html(f"""
<div class="metric-row">
  <div class="metric-chip">상태 <b>{project.status.value}</b></div>
  <div class="metric-chip">판정 <b>{decision_emoji} {decision_val}</b></div>
  <div class="metric-chip">품질 점수 <b>{final_score}</b></div>
  <div class="metric-chip">재작업 <b>{project.retry_count}회</b></div>
  <div class="metric-chip">예상 비용 <b>{project.estimated_cost:.4f}</b></div>
  <div class="metric-chip">LLM 호출 <b>{len(repos.costs.list_for_project(project.project_id))}회</b></div>
</div>
""")

st.divider()

# ═══════════════════════════════════════════════════════════════════════════════
# 1. AGENDA ROUTER 발언
# ═══════════════════════════════════════════════════════════════════════════════
if routing:
    _speech_start("card-router", "🧭  Agenda Router", "아젠다 분석")
    _html(f"""
    <div class="finding-item">난이도: <b>{routing.difficulty}</b></div>
    <div class="finding-item">주임 배정 수: <b>{routing.junior_count}명</b></div>
    <div class="finding-item">검증 강도: <b>{routing.verification_strength}</b></div>
    <div class="finding-item">추천 비용 모드: <b>{routing.recommended_cost_mode}</b></div>
    """)
    if routing.rationale:
        _html(f'<div style="margin-top:8px; font-size:13px; color:#94a3b8; font-style:italic;">"{routing.rationale}"</div>')
    _speech_end()
    _divider()

# ═══════════════════════════════════════════════════════════════════════════════
# 2. TASK SPLITTER — 업무 배정
# ═══════════════════════════════════════════════════════════════════════════════
if log.tasks:
    _speech_start("card-router", "📋  Task Splitter", "업무 분해")
    for t in log.tasks:
        _html(f'<div class="finding-item"><b>{t.assignee}</b> → {t.task_scope}</div>')
    _speech_end()
    _divider()

# ═══════════════════════════════════════════════════════════════════════════════
# 3. 주임 발언 (개별)
# ═══════════════════════════════════════════════════════════════════════════════
JUNIOR_CSS = {"junior_a": "card-junior-a", "junior_b": "card-junior-b", "junior_c": "card-junior-c"}
JUNIOR_ICON = {"junior_a": "👨‍💼 주임 A", "junior_b": "👨‍💼 주임 B", "junior_c": "👨‍💼 주임 C"}

if log.junior_outputs:
    _html('<div class="section-label" style="font-size:13px;color:#475569;margin-bottom:4px">💬 주임 발언</div>')

for jo in log.junior_outputs:
    css  = JUNIOR_CSS.get(jo.assignee, "card-junior-a")
    name = JUNIOR_ICON.get(jo.assignee, f"👨‍💼 {jo.assignee}")
    pkt  = jo.summary_packet

    _speech_start(css, name, jo.task_scope)

    # 조사 내용 원문 (있을 경우)
    if jo.content:
        _html(f'<div style="color:#94a3b8;font-size:13px;margin-bottom:10px;">{jo.content}</div>')

    _items("핵심 발견", pkt.key_findings, "finding-item")
    _items("출처", [f"{s.title}" + (f" — {s.summary}" if s.summary else "") for s in pkt.sources], "source-item")
    _items("불확실한 내용 (추가 검토 필요)", pkt.uncertain_points, "uncertain-item")

    if pkt.recommended_next_action:
        _html(f"""
        <div class="section-label">대리에게 전달</div>
        <div style="background:#1e293b;border-radius:6px;padding:8px 12px;
                    color:#cbd5e1;font-size:13px;">
            💬 &nbsp;{pkt.recommended_next_action}
        </div>""")

    _speech_end()

_divider()

# ═══════════════════════════════════════════════════════════════════════════════
# 4. 대리 발언 — 크로스 피드백 + 통합
# ═══════════════════════════════════════════════════════════════════════════════
deputy = repos.outputs.latest_deputy(project.project_id)
if deputy:
    _speech_start("card-deputy", "👩‍💼  대리", "검토 · 통합 · 초안 작성")

    # 주임별 피드백
    if deputy.junior_attribution:
        _html('<div class="section-label">주임 발언 검토</div>')
        for jid, comment in deputy.junior_attribution.items():
            jname = JUNIOR_ICON.get(jid, jid)
            _html(f'<div class="feedback-item"><b>{jname}</b>: {comment}</div>')

    # 핵심 주장
    if deputy.review_package.key_claims:
        _html('<div class="section-label">핵심 주장 및 근거</div>')
        for c in deputy.review_package.key_claims:
            src  = f" <span style='color:#475569'>({c.source})</span>" if c.source else ""
            conf_color = {"high":"#6ee7b7","medium":"#fcd34d","low":"#fca5a5"}.get(c.confidence,"#94a3b8")
            _html(f"""
            <div style="margin:6px 0;padding:8px 12px;background:#1a1505;border-radius:6px;">
              <span style="color:#e2e8f0">{c.claim}</span>{src}
              <span style="background:#292308;color:{conf_color};font-size:10px;
                     padding:1px 7px;border-radius:10px;margin-left:6px;">{c.confidence}</span>
              {"<div style='color:#94a3b8;font-size:12px;margin-top:3px;'>근거: "+c.evidence+"</div>" if c.evidence else ""}
            </div>""")

    # 제외 항목
    if deputy.excluded_items:
        _html('<div class="section-label">제외된 내용 및 사유</div>')
        for ex in deputy.excluded_items:
            _html(f'<div class="excluded-item">{ex.item} — {ex.reason}</div>')

    # 리스크
    if deputy.review_package.risk_points:
        _html('<div class="section-label">⚡ 리스크 포인트</div>')
        for rp in deputy.review_package.risk_points:
            _html(f'<div class="risk-item">{rp}</div>')

    # 추가 확인 필요
    if deputy.follow_up_questions:
        _html('<div class="section-label">추가 확인 필요 사항</div>')
        for q in deputy.follow_up_questions:
            _html(f'<div class="finding-item">{q}</div>')

    # 초안 보고서 (접어두기)
    with st.expander("📄 대리 초안 보고서 펼쳐보기", expanded=False):
        st.markdown(deputy.draft_report)

    _speech_end()
    _divider()

# ═══════════════════════════════════════════════════════════════════════════════
# 5. 부팀장 발언 — 최종 심사
# ═══════════════════════════════════════════════════════════════════════════════
if review:
    _speech_start("card-subleader", "🧑‍💼  부팀장", "품질검수 · 최종 판정")

    s = review.scores
    _html(f"""
    <div class="section-label">세부 점수</div>
    <div class="score-grid">
      <div class="score-item"><div class="score-label">사실성</div>
           <div class="score-value">{s.accuracy}</div></div>
      <div class="score-item"><div class="score-label">출처품질</div>
           <div class="score-value">{s.source_quality}</div></div>
      <div class="score-item"><div class="score-label">논리성</div>
           <div class="score-value">{s.logic}</div></div>
      <div class="score-item"><div class="score-label">완성도</div>
           <div class="score-value">{s.completeness}</div></div>
      <div class="score-item"><div class="score-label">할루시네이션</div>
           <div class="score-value">{s.hallucination_risk}</div></div>
      <div class="score-item" style="border:1px solid #334155;">
           <div class="score-label">평균</div>
           <div class="score-value" style="color:#a78bfa;">{s.average:.1f}</div></div>
    </div>""")

    dcls = {"APPROVED":"decision-approved",
            "CONDITIONAL_APPROVED":"decision-conditional",
            "REJECTED":"decision-rejected"}.get(review.decision.value,"decision-approved")
    dlabel = {"APPROVED":"✅ 승인","CONDITIONAL_APPROVED":"🟡 조건부 승인",
              "REJECTED":"❌ 반려"}.get(review.decision.value, review.decision.value)
    _html(f'<div class="section-label">최종 판정</div><div class="{dcls}">{dlabel}</div>')

    if review.feedback:
        _html(f"""
        <div class="section-label">피드백</div>
        <div style="background:#1c0a0a;border-radius:6px;padding:10px 14px;
                    color:#fecaca;font-size:13px;line-height:1.6;">
            💬 &nbsp;{review.feedback}
        </div>""")

    if review.retry_targets:
        _html('<div class="section-label">재작업 지시</div>')
        for t in review.retry_targets:
            _html(f'<div class="feedback-item"><b>{t.role.value}</b>'
                  f'{"("+t.assignee+")" if t.assignee else ""}: {t.reason}</div>')

    _speech_end()
    _divider()

# ═══════════════════════════════════════════════════════════════════════════════
# 6. 최종 보고서
# ═══════════════════════════════════════════════════════════════════════════════
if result.report:
    _speech_start("card-report", "📄  최종 보고서", "팀장 제출용")

    if result.report.is_partial:
        _html('<div class="uncertain-item" style="margin-bottom:8px;">'
              'Circuit Breaker 작동 — 한계가 포함된 보고서입니다.</div>')

    _speech_end()

    with st.container():
        st.markdown(result.report.markdown)
        st.download_button(
            "📥 보고서 다운로드 (.md)",
            data=result.report.markdown,
            file_name=f"report_{project.project_id}.md",
            mime="text/markdown",
            use_container_width=True,
        )
