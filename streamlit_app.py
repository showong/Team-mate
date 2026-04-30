"""Team-mate — AI 가상 팀 라이브 미팅룸

아젠다 입력 → 백그라운드에서 워크플로우 실행 → 회의 진행 과정을 실시간 채팅으로
스트리밍 재생합니다. 참여자 5명(주임 A/B/C, 대리, 부팀장)이 한 화면에 동시 노출되며,
발언 중인 사람만 강조됩니다.

실행: streamlit run streamlit_app.py
"""

from __future__ import annotations

import html
import time
from datetime import datetime
from typing import Optional

import streamlit as st

# ── 페이지 설정 ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Team-mate | Live Meeting",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

from app.core.orchestrator import Orchestrator
from app.llm.mock_client import MockLLMClient
from app.llm.multi_provider_client import MultiProviderLLMClient
from app.schemas import ProjectCreate
from app.schemas.project import CostMode, OutputLength, VerificationLevel
from app.storage.database import get_repositories, reset_repositories


# ═══════════════════════════════════════════════════════════════════════════════
# Provider × 모델 카탈로그
# ═══════════════════════════════════════════════════════════════════════════════
# 주임용 (가성비) — 각 provider 의 저비용 모델
JUNIOR_MODELS = {
    "Anthropic": ["claude-haiku-4-5-20251001"],
    "OpenAI":    ["gpt-4o-mini"],
    "Gemini":    ["gemini-1.5-flash", "gemini-2.0-flash"],
    "Mock":      ["mock"],
}

# 대리·부팀장용 (고사양) — 각 provider 의 플래그십 모델
HIGH_END_MODELS = {
    "Anthropic": ["claude-sonnet-4-6", "claude-opus-4-7"],
    "OpenAI":    ["gpt-4o", "o1-mini"],
    "Gemini":    ["gemini-1.5-pro"],
    "Mock":      ["mock"],
}

# 사용자 요청 기본값 — 주임 A/B/C 가 각각 Anthropic/OpenAI/Gemini
DEFAULTS = {
    "junior_a": ("Anthropic", "claude-haiku-4-5-20251001"),
    "junior_b": ("OpenAI",    "gpt-4o-mini"),
    "junior_c": ("Gemini",    "gemini-1.5-flash"),
    "deputy":   ("Anthropic", "claude-sonnet-4-6"),
    "subleader":("Anthropic", "claude-opus-4-7"),
}


# ═══════════════════════════════════════════════════════════════════════════════
# 색상/아바타 매핑
# ═══════════════════════════════════════════════════════════════════════════════
ROLES = {
    "router":    {"name": "Router",    "avatar": "🧭", "color": "#94a3b8", "scope": "아젠다 분석"},
    "splitter":  {"name": "Splitter",  "avatar": "📋", "color": "#a78bfa", "scope": "업무 분해"},
    "junior_a":  {"name": "주임 A",     "avatar": "🔵", "color": "#3b82f6", "scope": "시장·배경"},
    "junior_b":  {"name": "주임 B",     "avatar": "🟦", "color": "#06b6d4", "scope": "직무·역량"},
    "junior_c":  {"name": "주임 C",     "avatar": "🟢", "color": "#10b981", "scope": "사례·적용"},
    "deputy":    {"name": "대리",       "avatar": "🟠", "color": "#f59e0b", "scope": "검토·통합"},
    "subleader": {"name": "부팀장",     "avatar": "🔴", "color": "#ef4444", "scope": "품질검수"},
    "report":    {"name": "최종 보고서","avatar": "📄", "color": "#a78bfa", "scope": ""},
}


# ═══════════════════════════════════════════════════════════════════════════════
# CSS
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
.stApp { background-color: #0f1117; }

/* 미팅룸 헤더 */
.meeting-header {
    background: linear-gradient(135deg, #1e3a5f 0%, #0d2137 100%);
    border: 1px solid #2d5986;
    border-radius: 12px;
    padding: 16px 24px;
    margin-bottom: 18px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.meeting-title { font-size: 18px; font-weight: 700; color: #e2e8f0; }
.meeting-sub   { font-size: 12px; color: #94a3b8; margin-top: 2px; }
.live-dot {
    display: inline-block; width: 10px; height: 10px; border-radius: 50%;
    background: #ef4444; margin-right: 6px;
    animation: pulse 1.5s ease-in-out infinite;
}
@keyframes pulse { 0%,100% {opacity:1;} 50% {opacity:0.3;} }

/* 참여자 타일 그리드 */
.participants {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 10px;
    margin-bottom: 18px;
}
.tile {
    background: #1a1f2e;
    border: 2px solid #1e293b;
    border-radius: 12px;
    padding: 12px;
    transition: all 0.3s;
    min-height: 140px;
    position: relative;
}
.tile.waiting   { opacity: 0.45; }
.tile.speaking  { box-shadow: 0 0 22px rgba(59,130,246,0.5); transform: translateY(-2px); }
.tile.done      { opacity: 0.95; }
.tile.speaking::before {
    content: "🔴 LIVE"; position: absolute; top: -8px; right: 10px;
    background: #ef4444; color: white; font-size: 9px; font-weight: 700;
    padding: 2px 7px; border-radius: 8px; letter-spacing: 0.05em;
    animation: pulse 1.5s ease-in-out infinite;
}

.tile-avatar { font-size: 28px; }
.tile-name   { font-size: 13px; font-weight: 700; color: #e2e8f0; margin-top: 4px; }
.tile-scope  { font-size: 10px; color: #64748b; margin-top: 2px; }
.tile-status { font-size: 11px; color: #94a3b8; margin-top: 8px; font-style: italic; }
.tile-summary {
    font-size: 11px; color: #cbd5e1; margin-top: 6px; line-height: 1.4;
    border-top: 1px solid #1e293b; padding-top: 6px; max-height: 60px;
    overflow: hidden;
}

/* 채팅 영역 */
.chat-thread {
    background: #0d1019;
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 14px 18px;
    max-height: 600px;
    overflow-y: auto;
}
.chat-header {
    font-size: 12px; color: #475569; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.1em;
    border-bottom: 1px solid #1e293b; padding-bottom: 8px; margin-bottom: 10px;
}

/* 채팅 메시지 */
.msg { display: flex; gap: 10px; margin: 8px 0; align-items: flex-start; }
.msg-avatar {
    width: 28px; height: 28px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 16px; flex-shrink: 0;
    background: #1e293b;
}
.msg-body { flex: 1; min-width: 0; }
.msg-meta { font-size: 11px; color: #64748b; margin-bottom: 2px; }
.msg-meta b { color: #cbd5e1; font-size: 12px; }
.msg-arrow {
    display: inline-block;
    background: #1e293b; color: #94a3b8;
    font-size: 10px; padding: 1px 6px; border-radius: 8px;
    margin-left: 6px;
}
.msg-bubble {
    background: #1a1f2e; border-radius: 10px;
    padding: 8px 12px; color: #e2e8f0; font-size: 13px;
    line-height: 1.55; border-left: 3px solid #475569;
}
.msg-bubble.uncertain { border-left-color: #fbbf24; background: #1c1709; }
.msg-bubble.risk      { border-left-color: #ef4444; background: #1c0a0a; }
.msg-bubble.feedback  { border-left-color: #f59e0b; background: #1c1305; }
.msg-bubble.verdict   { border-left-color: #a78bfa; background: #150d2e; font-weight: 600; }
.msg-bubble.system    { border-left-color: #94a3b8; background: #0f172a; font-style: italic;
                        color: #94a3b8; font-size: 12px; }

/* 결과 패널 */
.score-grid { display: grid; grid-template-columns: repeat(6, 1fr); gap: 8px; margin: 10px 0; }
.score-cell { background: #1a1f2e; border-radius: 8px; padding: 10px 6px; text-align: center; }
.score-cell .lbl { font-size: 9px; color: #64748b; text-transform: uppercase; }
.score-cell .val { font-size: 22px; font-weight: 700; color: #e2e8f0; }
.score-cell.avg .val { color: #a78bfa; }

.verdict-banner {
    border-radius: 10px; padding: 14px 22px; font-size: 17px; font-weight: 700;
    text-align: center; margin: 12px 0;
}
.verdict-approved   { background:#065f46; color:#6ee7b7; border:1px solid #059669; }
.verdict-conditional{ background:#78350f; color:#fcd34d; border:1px solid #d97706; }
.verdict-rejected   { background:#7f1d1d; color:#fca5a5; border:1px solid #dc2626; }

.metric-bar { display:flex; gap:10px; flex-wrap: wrap; }
.metric-chip {
    background:#1a1f2e; border:1px solid #1e293b; border-radius:18px;
    padding:5px 14px; font-size:12px; color:#94a3b8;
}
.metric-chip b { color:#e2e8f0; }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# 세션 상태
# ═══════════════════════════════════════════════════════════════════════════════
def _init_state() -> None:
    for k, v in {
        "result": None,
        "ran_once": False,
    }.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()


# ═══════════════════════════════════════════════════════════════════════════════
# 사이드바
# ═══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### 🏢 Team-mate")
    st.caption("AI 가상부서 라이브 미팅")
    st.divider()

    speed = st.select_slider(
        "🎬 재생 속도",
        options=["느리게", "보통", "빠르게", "즉시"],
        value="보통",
        help="채팅 메시지 등장 간격",
    )
    SPEED_MAP = {"느리게": 0.8, "보통": 0.4, "빠르게": 0.15, "즉시": 0.0}
    delay = SPEED_MAP[speed]

    st.divider()
    cost_mode = st.selectbox("비용 모드",
        [m.value for m in CostMode], index=1)
    verification_level = st.selectbox("검증 강도",
        [v.value for v in VerificationLevel], index=1)
    output_length = st.selectbox("보고서 길이",
        [o.value for o in OutputLength], index=1)

    st.divider()
    test_mode = st.toggle(
        "🤖 Mock 모드 (모든 역할)",
        value=True,
        help="끄면 역할별로 실제 LLM 모델을 선택합니다.",
    )

    role_models: dict[str, str] = {}

    if not test_mode:
        st.markdown("**🔑 API Keys**")
        with st.expander("API Key 입력", expanded=True):
            openai_key    = st.text_input("OpenAI",    type="password",
                                           placeholder="sk-...", key="openai_key")
            anthropic_key = st.text_input("Anthropic", type="password",
                                           placeholder="sk-ant-...", key="anthropic_key")
            gemini_key    = st.text_input("Gemini",    type="password",
                                           placeholder="AIza...", key="gemini_key")

        st.markdown("**🎭 역할별 모델 선택**")

        def _role_picker(label: str, role_key: str, catalog: dict) -> Optional[str]:
            """provider + model 2단계 selector. 선택값을 model 이름으로 반환."""
            default_provider, default_model = DEFAULTS[role_key]
            providers = list(catalog.keys())
            prov_idx = providers.index(default_provider) if default_provider in providers else 0

            with st.container():
                st.caption(label)
                col_a, col_b = st.columns([1, 2])
                with col_a:
                    provider = st.selectbox(
                        "Provider", providers, index=prov_idx,
                        key=f"{role_key}_provider", label_visibility="collapsed",
                    )
                models = catalog[provider]
                model_idx = models.index(default_model) if default_model in models else 0
                with col_b:
                    model = st.selectbox(
                        "Model", models, index=model_idx,
                        key=f"{role_key}_model", label_visibility="collapsed",
                    )
                return None if model == "mock" else model

        role_models["junior_a"]  = _role_picker("👨‍💼 주임 A — 시장·배경",  "junior_a",  JUNIOR_MODELS)
        role_models["junior_b"]  = _role_picker("👨‍💼 주임 B — 직무·역량",  "junior_b",  JUNIOR_MODELS)
        role_models["junior_c"]  = _role_picker("👨‍💼 주임 C — 사례·적용",  "junior_c",  JUNIOR_MODELS)
        role_models["deputy"]    = _role_picker("👩‍💼 대리 — 검토·통합",     "deputy",    HIGH_END_MODELS)
        role_models["subleader"] = _role_picker("🧑‍💼 부팀장 — 품질검수",   "subleader", HIGH_END_MODELS)

        # Router/Splitter 는 비용 절약 위해 mock 또는 가장 저렴한 주임 모델과 동일하게
        role_models["router"]   = role_models["junior_a"]
        role_models["splitter"] = role_models["junior_a"]
    else:
        st.info("Mock 모드 — API Key 불필요. 모든 역할이 동일한 mock 응답을 반환합니다.", icon="🤖")
        openai_key = anthropic_key = gemini_key = ""

    st.divider()
    if st.button("🗑️ 미팅 초기화", use_container_width=True):
        reset_repositories()
        st.session_state.result = None
        st.session_state.ran_once = False
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# 헤더 + 입력 폼
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="meeting-header">
  <div>
    <div class="meeting-title">🎙️ Team-mate Live Meeting</div>
    <div class="meeting-sub">AI 가상 팀이 한 화면에서 토의하고 피드백을 주고받습니다</div>
  </div>
  <div style="font-size:12px;color:#64748b">{datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
</div>
""", unsafe_allow_html=True)

with st.form("agenda_form"):
    agenda = st.text_area("📋 아젠다 (조사 주제)",
        placeholder="예) 중국 AI 트레이너 시장의 역할, 직무, 필요역량을 조사해줘.",
        height=80)
    c1, c2 = st.columns(2)
    purpose    = c1.text_input("🎯 목적",    placeholder="예) 커리어 확장 가능성 판단")
    conditions = c2.text_input("📌 특이사항", placeholder="예) 금융 분야에 가중치")
    submitted  = st.form_submit_button("🚀 미팅 시작", use_container_width=True, type="primary")


# ═══════════════════════════════════════════════════════════════════════════════
# 헬퍼: 타일 렌더
# ═══════════════════════════════════════════════════════════════════════════════
TILE_ROLES = ["junior_a", "junior_b", "junior_c", "deputy", "subleader"]


def render_tiles(states: dict) -> str:
    """states[role] = {'state': 'waiting'|'speaking'|'done', 'status_text': str, 'summary': str}"""
    cells = []
    for role in TILE_ROLES:
        info = ROLES[role]
        s = states.get(role, {"state": "waiting", "status_text": "대기 중", "summary": ""})
        state = s["state"]
        status_text = html.escape(s.get("status_text", ""))
        summary = s.get("summary", "")
        summary_html = f'<div class="tile-summary">{summary}</div>' if summary else ""
        cells.append(f"""
        <div class="tile {state}" style="border-color:{info['color'] if state != 'waiting' else '#1e293b'}">
          <div class="tile-avatar">{info['avatar']}</div>
          <div class="tile-name" style="color:{info['color']}">{info['name']}</div>
          <div class="tile-scope">{info['scope']}</div>
          <div class="tile-status">{status_text}</div>
          {summary_html}
        </div>""")
    return f'<div class="participants">{"".join(cells)}</div>'


def render_chat(messages: list) -> str:
    """Render full chat thread."""
    out = ['<div class="chat-thread"><div class="chat-header">💬 미팅 진행 (실시간)</div>']
    for m in messages:
        speaker = ROLES[m["from"]]
        target_html = ""
        if m.get("to") and m["to"] in ROLES:
            target = ROLES[m["to"]]
            target_html = f'<span class="msg-arrow">→ {target["avatar"]} {target["name"]}</span>'
        bubble_cls = m.get("style", "")
        out.append(f"""
        <div class="msg">
          <div class="msg-avatar">{speaker['avatar']}</div>
          <div class="msg-body">
            <div class="msg-meta">
              <b style="color:{speaker['color']}">{speaker['name']}</b>{target_html}
              <span style="float:right">{m.get('ts','')}</span>
            </div>
            <div class="msg-bubble {bubble_cls}">{html.escape(m['msg']).replace(chr(10),'<br>')}</div>
          </div>
        </div>""")
    out.append('</div>')
    return "".join(out)


# ═══════════════════════════════════════════════════════════════════════════════
# 미팅 실행 & 라이브 재생
# ═══════════════════════════════════════════════════════════════════════════════
def play_meeting(result, delay: float, tile_slot, chat_slot, footer_slot) -> None:
    """워크플로우 결과를 받아 채팅 타임라인으로 점진적으로 재생."""

    project = result.project
    routing = result.routing
    log     = result.log
    review  = result.review
    repos   = get_repositories()
    deputy  = repos.outputs.latest_deputy(project.project_id)

    # 초기 상태
    states = {r: {"state": "waiting", "status_text": "대기 중", "summary": ""} for r in TILE_ROLES}
    chat = []

    def now() -> str:
        return datetime.now().strftime("%H:%M:%S")

    def push(speaker: str, msg: str, target: Optional[str] = None, style: str = "") -> None:
        chat.append({"from": speaker, "to": target, "msg": msg, "ts": now(), "style": style})
        chat_slot.markdown(render_chat(chat), unsafe_allow_html=True)
        time.sleep(delay)

    def update_tiles() -> None:
        tile_slot.markdown(render_tiles(states), unsafe_allow_html=True)

    def set_state(role: str, state: str, status: str = "", summary: str = "") -> None:
        if role in states:
            states[role] = {"state": state, "status_text": status, "summary": summary}
            update_tiles()
            time.sleep(delay * 0.5)

    # ── 시작 ────────────────────────────────────────────────────────────────
    update_tiles()
    push("router", f"오늘 아젠다는 \"{project.agenda}\" 입니다. 분석 시작하겠습니다.", style="system")

    # 1. Router
    if routing:
        push("router",
             f"난이도 {routing.difficulty} / 검증 {routing.verification_strength} / 주임 {routing.junior_count}명 배정이 적정합니다.")
        if routing.rationale:
            push("router", f"판단 근거: {routing.rationale}", style="system")

    # 2. Splitter — 각 주임에게 업무 배정
    if log.tasks:
        push("splitter", "업무 분해 결과 공유드리겠습니다.")
        for t in log.tasks:
            push("splitter", t.task_scope, target=t.assignee)
            if t.assignee in states:
                set_state(t.assignee, "waiting", status="배정 받음")

    # 3. 주임 발언 — 한 명씩 라이브
    for jo in log.junior_outputs:
        rid = jo.assignee
        if rid not in states:
            continue

        set_state(rid, "speaking", status="발언 중...")

        push(rid, f"제가 맡은 \"{jo.task_scope}\" 조사 결과 공유드립니다.")

        # 핵심 발견 — 항목별로 메시지
        for f in jo.summary_packet.key_findings:
            push(rid, f)

        # 출처
        if jo.summary_packet.sources:
            sources_text = "\n".join(
                f"• {s.title}" + (f" — {s.summary}" if s.summary else "")
                for s in jo.summary_packet.sources
            )
            push(rid, f"근거 자료:\n{sources_text}", style="system")

        # 불확실 → 대리에게 질문
        for u in jo.summary_packet.uncertain_points:
            push(rid, u, target="deputy", style="uncertain")

        if jo.summary_packet.recommended_next_action:
            push(rid, jo.summary_packet.recommended_next_action,
                 target="deputy", style="feedback")

        # 발언 종료 — 요약 박제
        summary = " · ".join(jo.summary_packet.key_findings[:2])
        set_state(rid, "done", status=f"발언 완료 ({len(jo.summary_packet.key_findings)}개 발견)",
                  summary=summary)

    # 4. 대리 — 각 주임에게 크로스 피드백 (핵심!)
    if deputy:
        set_state("deputy", "speaking", status="피드백 정리 중...")

        push("deputy", "주임 여러분 발언 잘 들었습니다. 한 분씩 의견 드리겠습니다.")

        # 주임별 피드백 (cross-reference 명시)
        for jid, comment in deputy.junior_attribution.items():
            push("deputy", comment, target=jid, style="feedback")

        # 핵심 주장 정리
        if deputy.review_package.key_claims:
            push("deputy", "통합한 핵심 주장은 다음과 같습니다:")
            for c in deputy.review_package.key_claims:
                conf_emoji = {"high": "✅", "medium": "🔸", "low": "⚠️"}.get(c.confidence, "")
                src = f" ({c.source})" if c.source else ""
                push("deputy", f"{conf_emoji} {c.claim}{src}")

        # 제외 항목 (피드백 형태)
        for ex in deputy.excluded_items:
            push("deputy", f"\"{ex.item}\" 은 제외했습니다 — {ex.reason}", style="system")

        # 리스크
        for rp in deputy.review_package.risk_points:
            push("deputy", rp, style="risk")

        # 부팀장에게 검수 요청
        if deputy.follow_up_questions:
            for q in deputy.follow_up_questions:
                push("deputy", q, target="subleader", style="feedback")
        else:
            push("deputy", "이상으로 통합 초안 작성 마쳤습니다. 부팀장님 검수 부탁드립니다.",
                 target="subleader")

        summary = f"{len(deputy.review_package.key_claims)} 핵심주장 · {len(deputy.review_package.risk_points)} 리스크"
        set_state("deputy", "done", status="통합 완료", summary=summary)

    # 5. 부팀장 — 점수 + 판정 + 재작업 지시 (cross-reference)
    if review:
        set_state("subleader", "speaking", status="검수 중...")

        push("subleader", "검수 들어가겠습니다.")

        s = review.scores
        push("subleader",
             f"점수표: 사실성 {s.accuracy} · 출처 {s.source_quality} · 논리 {s.logic} · 완성도 {s.completeness} · 할루시네이션 안전도 {s.hallucination_risk} → 평균 {s.average:.1f}")

        if review.feedback:
            push("subleader", review.feedback, style="feedback")

        # 재작업 지시 — 누구에게인지 명시
        for t in review.retry_targets:
            target_role = t.assignee if t.assignee else t.role.value
            push("subleader", t.reason, target=target_role, style="risk")

        # 최종 판정
        verdict_label = {
            "APPROVED": "✅ 승인합니다.",
            "CONDITIONAL_APPROVED": "🟡 조건부 승인합니다. 대리 수정 후 제출.",
            "REJECTED": "❌ 반려합니다.",
        }.get(review.decision.value, review.decision.value)
        push("subleader", verdict_label, style="verdict")

        set_state("subleader", "done",
                  status=f"판정: {review.decision.value}",
                  summary=f"평균 점수 {s.average:.1f}/5.0")

    # 6. 미팅 종료 안내
    if result.report and result.report.is_partial:
        push("router", "Circuit Breaker 작동으로 한계가 포함된 보고서가 생성되었습니다.",
             style="risk")
    push("router", "미팅 종료. 모두 수고하셨습니다.", style="system")

    # 결과 패널 표시
    render_results_panel(result, footer_slot)


def render_results_panel(result, slot) -> None:
    """채팅 아래에 점수표/판정/보고서 패널."""
    project = result.project
    review = result.review
    repos = get_repositories()

    with slot.container():
        st.markdown("### 📊 미팅 결과 요약")

        # 메트릭
        decision_val = review.decision.value if review else "-"
        decision_emoji = {"APPROVED": "✅", "CONDITIONAL_APPROVED": "🟡", "REJECTED": "❌"}.get(decision_val, "")
        avg = f"{review.scores.average:.1f}" if review else "-"
        n_calls = len(repos.costs.list_for_project(project.project_id))

        st.markdown(f"""
        <div class="metric-bar">
          <div class="metric-chip">상태 <b>{project.status.value}</b></div>
          <div class="metric-chip">판정 <b>{decision_emoji} {decision_val}</b></div>
          <div class="metric-chip">평균 점수 <b>{avg}/5.0</b></div>
          <div class="metric-chip">재작업 <b>{project.retry_count}회</b></div>
          <div class="metric-chip">예상 비용 <b>{project.estimated_cost:.4f}</b></div>
          <div class="metric-chip">LLM 호출 <b>{n_calls}회</b></div>
        </div>
        """, unsafe_allow_html=True)

        # 판정 배너
        if review:
            cls = {"APPROVED": "verdict-approved",
                   "CONDITIONAL_APPROVED": "verdict-conditional",
                   "REJECTED": "verdict-rejected"}.get(review.decision.value, "verdict-approved")
            label = {"APPROVED": "✅ 승인 — 보고서 제출 가능",
                     "CONDITIONAL_APPROVED": "🟡 조건부 승인 — 대리 수정 후 제출",
                     "REJECTED": "❌ 반려"}.get(review.decision.value, review.decision.value)
            st.markdown(f'<div class="verdict-banner {cls}">{label}</div>',
                        unsafe_allow_html=True)

        # 최종 보고서 (접기)
        if result.report:
            with st.expander("📄 최종 보고서 펼쳐보기", expanded=False):
                st.markdown(result.report.markdown)
                st.download_button(
                    "📥 다운로드 (.md)",
                    data=result.report.markdown,
                    file_name=f"report_{project.project_id}.md",
                    mime="text/markdown",
                    use_container_width=True,
                )


# ═══════════════════════════════════════════════════════════════════════════════
# 폼 제출 처리
# ═══════════════════════════════════════════════════════════════════════════════
if submitted:
    if not agenda.strip():
        st.warning("아젠다를 입력해주세요.")
        st.stop()

    payload = ProjectCreate(
        agenda=agenda.strip(),
        purpose=purpose.strip() or None,
        conditions=conditions.strip() or None,
        cost_mode=CostMode(cost_mode),
        verification_level=VerificationLevel(verification_level),
        output_length=OutputLength(output_length),
    )

    # ---- LLM 클라이언트 + 역할별 모델 매핑 ----
    if test_mode:
        llm = MockLLMClient()
        active_overrides: dict = {}
    else:
        # 선택된 모델들 중 실제로 어떤 provider 가 사용되는지 검증
        used_providers: set = set()
        for v in role_models.values():
            if not v:
                continue
            if v.startswith("claude-"):
                used_providers.add("anthropic")
            elif v.startswith("gpt-") or v.startswith("o1-") or v.startswith("o3-"):
                used_providers.add("openai")
            elif v.startswith("gemini-"):
                used_providers.add("gemini")

        # 사용 provider 의 키가 비어있으면 경고
        missing = []
        if "openai" in used_providers and not openai_key:
            missing.append("OpenAI")
        if "anthropic" in used_providers and not anthropic_key:
            missing.append("Anthropic")
        if "gemini" in used_providers and not gemini_key:
            missing.append("Gemini")
        if missing:
            st.error(
                f"선택한 모델이 다음 provider를 사용하는데 API Key가 비어있습니다: "
                f"{', '.join(missing)}. 미입력 provider는 자동으로 Mock으로 대체됩니다."
            )

        try:
            llm = MultiProviderLLMClient(
                openai_api_key=openai_key or None,
                anthropic_api_key=anthropic_key or None,
                gemini_api_key=gemini_key or None,
                fallback_to_mock=True,
            )
        except Exception as e:
            st.error(f"LLM 초기화 실패: {e}")
            st.stop()

        # 빈 값(None) 제거
        active_overrides = {k: v for k, v in role_models.items() if v}

    repos = get_repositories()
    orch  = Orchestrator(
        repos=repos,
        llm=llm,
        model_overrides=active_overrides if active_overrides else None,
    )

    with st.spinner("백그라운드에서 미팅 준비 중..."):
        project = orch.create_project(payload)
        result  = orch.run_project(project.project_id)
        st.session_state.result   = result
        st.session_state.ran_once = True


# ═══════════════════════════════════════════════════════════════════════════════
# 메인 미팅 화면 — 타일 + 채팅 + 결과 (3단)
# ═══════════════════════════════════════════════════════════════════════════════
result = st.session_state.get("result")

if result is None:
    # 미팅 시작 전 빈 화면
    empty_states = {r: {"state": "waiting", "status_text": "대기 중", "summary": ""} for r in TILE_ROLES}
    st.markdown(render_tiles(empty_states), unsafe_allow_html=True)
    st.markdown(render_chat([{
        "from": "router", "to": None, "msg": "아젠다를 입력하시면 미팅을 시작합니다.",
        "ts": "--:--:--", "style": "system",
    }]), unsafe_allow_html=True)
else:
    tile_slot   = st.empty()
    chat_slot   = st.empty()
    footer_slot = st.empty()

    if submitted:
        # 새로 제출된 경우 — 라이브 재생
        play_meeting(result, delay, tile_slot, chat_slot, footer_slot)
    else:
        # 페이지 새로고침 등으로 다시 표시 — 즉시 모두 출력
        play_meeting(result, 0.0, tile_slot, chat_slot, footer_slot)
