"""AutoHeal EvidenceFirst (CTRL+AI Challenge PS-12 Auto-Heal).
Autonomous SRE incident response console with code-enforced safety gates,
deterministic simulator, and competing root-cause hypothesis board.
"""

import os
import time
import streamlit as st

# Configure Streamlit page settings before any UI calls
st.set_page_config(
    page_title="AutoHeal EvidenceFirst",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

from ui.theme import CUSTOM_CSS
from ui.topology_svg import render_topology_svg
from ui.components import (
    render_top_bar,
    render_alert_card,
    render_hypothesis_board,
    render_timeline,
    render_approval_card,
    render_escalation_card,
    render_resolved_banner,
    render_memory_comparison_chart,
)
from core.state import init_state, reset_environment
from core.faults import inject_cache_outage, inject_bad_config, inject_db_integrity
from core.agent import run_agent, resume_after_approval

# Inject custom theme CSS
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# 1. State initialization
if "S" not in st.session_state:
    st.session_state["S"] = init_state()

S = st.session_state["S"]

# 2. Key and client resolution
# Empty key = start in reliable fallback policy, never crash
api_key = ""
try:
    api_key = st.secrets.get("GEMINI_API_KEY", "")
except Exception:
    pass
if not api_key:
    api_key = os.environ.get("GEMINI_API_KEY", "")

gemini_client = None
if api_key:
    try:
        from google import genai
        gemini_client = genai.Client(api_key=api_key)
        S["mode"] = "gemini"
        S["mode_reason"] = ""
    except Exception as e:
        S["mode"] = "fallback"
        S["mode_reason"] = f"SDK initialization failed: {str(e)[:40]}"
else:
    S["mode"] = "fallback"
    S["mode_reason"] = "No GEMINI_API_KEY detected in secrets"

# 3. Sidebar: Demo Chaos Controls
chaos_gate_pass = False
try:
    expected_code = st.secrets.get("CHAOS_ACCESS_CODE", "")
except Exception:
    expected_code = os.environ.get("CHAOS_ACCESS_CODE", "")

with st.sidebar:
    st.markdown('<div class="mc-header-label">DEMO CONTROL GATE</div>', unsafe_allow_html=True)
    st.caption("Access gate for injecting simulated faults into the orders platform.")

    if expected_code:
        input_code = st.text_input("Access Code", type="password", key="access_code_input")
        chaos_gate_pass = (input_code == expected_code)
        if not chaos_gate_pass:
            st.warning("Enter correct demo access code to unlock chaos injection.")
    else:
        chaos_gate_pass = True

    st.markdown("---")
    st.markdown('<div class="mc-header-label">CHAOS FAULT INJECTION</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Cache Outage", use_container_width=True, disabled=not chaos_gate_pass):
            # Check if cache outage happened before for memory scenario
            has_prior_cache = any("cache" in m.get("signature", "") for m in S.get("memory", []))
            reset_environment(S)
            inject_cache_outage(S, is_repeat=has_prior_cache)
            st.rerun()

    with c2:
        if st.button("Bad Config", use_container_width=True, disabled=not chaos_gate_pass):
            reset_environment(S)
            inject_bad_config(S)
            st.rerun()

    c3, c4 = st.columns(2)
    with c3:
        if st.button("DB Integrity", use_container_width=True, disabled=not chaos_gate_pass):
            reset_environment(S)
            inject_db_integrity(S)
            st.rerun()

    with c4:
        if st.button("Reset Baseline", use_container_width=True):
            reset_environment(S)
            st.rerun()

    st.markdown("---")
    st.markdown('<div class="mc-header-label">RUNTIME TELEMETRY</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div style="font-size: 12px; color: #8B96AD;" class="mono">
      <div>MODE: <span style="color: {'#38BDF8' if S['mode'] == 'gemini' else '#F59E0B'}">{S['mode'].upper()}</span></div>
      <div>LLM CALLS: <span style="color: #F1F5F9">{S.get('llm_calls', 0)}</span></div>
      <div>DIAG CALLS: <span style="color: #F1F5F9">{S.get('diag_calls', 0)}/5</span></div>
      <div>RESOLVED IN MEMORY: <span style="color: #22C55E">{len(S.get('memory', []))}</span></div>
    </div>
    """, unsafe_allow_html=True)

# 4. Main Console Layout
# Placeholders for live streaming agent turns
top_slot = st.empty()
alert_slot = st.empty()
col_left, col_right = st.columns([5, 7])
with col_left:
    topo_slot = st.empty()
with col_right:
    hyp_slot = st.empty()
approval_slot = st.empty()
escalation_slot = st.empty()
resolved_slot = st.empty()
timeline_slot = st.empty()
chart_slot = st.empty()

def update_ui():
    """Refresh UI slots from current state S."""
    top_slot.markdown(render_top_bar(S), unsafe_allow_html=True)
    alert_slot.markdown(render_alert_card(S), unsafe_allow_html=True)
    topo_slot.markdown(render_topology_svg(S), unsafe_allow_html=True)
    hyp_slot.markdown(render_hypothesis_board(S), unsafe_allow_html=True)
    timeline_slot.markdown(render_timeline(S), unsafe_allow_html=True)

    if S.get("phase") == "AWAITING_APPROVAL":
        approval_slot.markdown(render_approval_card(S), unsafe_allow_html=True)
    else:
        approval_slot.empty()

    if S.get("phase") == "ESCALATED":
        escalation_slot.markdown(render_escalation_card(S), unsafe_allow_html=True)
    else:
        escalation_slot.empty()

    if S.get("phase") == "RESOLVED":
        resolved_slot.markdown(render_resolved_banner(S), unsafe_allow_html=True)
        chart = render_memory_comparison_chart(S)
        if chart:
            chart_slot.plotly_chart(chart, use_container_width=True)
        else:
            chart_slot.empty()
    else:
        resolved_slot.empty()
        chart_slot.empty()

# Render initial view
update_ui()

# 5. Interactive Action Triggers
# INVESTIGATE Button
if S.get("incident") and S.get("phase") == "INVESTIGATING":
    btn_label = "Investigate & Auto-Heal (Agent Loop)"
    if st.button(btn_label, type="primary", use_container_width=True):
        def step_refresh(updated_S):
            update_ui()
            time.sleep(0.8)  # Paced visual updates for judges

        run_agent(S, client=gemini_client, on_step=step_refresh)
        update_ui()
        st.rerun()

# APPROVAL Controls (when AWAITING_APPROVAL)
if S.get("phase") == "AWAITING_APPROVAL":
    st.markdown('<div class="mc-header-label">HUMAN SUPERVISOR DECISION</div>', unsafe_allow_html=True)
    col_app, col_rej = st.columns(2)
    with col_app:
        if st.button("Approve Proposed Rollback", type="primary", use_container_width=True):
            def step_refresh(updated_S):
                update_ui()
                time.sleep(0.8)

            resume_after_approval(S, client=gemini_client, approved=True, on_step=step_refresh)
            update_ui()
            st.rerun()
    with col_rej:
        if st.button("Reject Action (Page Human)", use_container_width=True):
            def step_refresh(updated_S):
                update_ui()
                time.sleep(0.8)

            resume_after_approval(S, client=gemini_client, approved=False, on_step=step_refresh)
            update_ui()
            st.rerun()
