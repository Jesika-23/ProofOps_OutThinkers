"""Pure presentation components for AutoHeal EvidenceFirst Mission Control."""

from typing import Any, Dict, List, Optional
import time
import plotly.graph_objects as go
from core.memory import get_memory_comparison


def render_top_bar(S: Dict[str, Any]) -> str:
    """Render top application header with product title, mode pill, phase, and incident ID."""
    mode = S.get("mode", "gemini")
    mode_reason = S.get("mode_reason", "")
    phase = S.get("phase", "IDLE")
    incident = S.get("incident")
    inc_id = incident.get("id", "NO ACTIVE INCIDENT") if incident else "SYSTEM NOMINAL"

    if mode == "gemini":
        mode_pill = '<span class="chip chip-agent">GEMINI 2.5 REASONING</span>'
    else:
        reason_text = f" ({mode_reason})" if mode_reason else ""
        mode_pill = f'<span class="chip chip-amber">RELIABLE FALLBACK POLICY{reason_text}</span>'

    phase_classes = {
        "IDLE": "chip-system",
        "INVESTIGATING": "chip-amber",
        "AWAITING_APPROVAL": "chip-amber",
        "REMEDIATING": "chip-agent",
        "VERIFYING": "chip-agent",
        "RESOLVED": "chip-healthy",
        "ESCALATED": "chip-critical",
    }
    phase_chip = f'<span class="chip {phase_classes.get(phase, "chip-system")}">{phase}</span>'

    return f"""
<div style="display: flex; justify-content: space-between; align-items: center; padding: 14px 18px; background: #121826; border: 1px solid #25304A; border-radius: 12px; margin-bottom: 16px;">
  <div style="display: flex; align-items: baseline; gap: 12px;">
    <span style="font-size: 16px; font-weight: 700; letter-spacing: 0.04em; color: #F8FAFC;">AUTOHEAL <span style="color: #38BDF8;">EVIDENCEFIRST</span></span>
    <span style="font-size: 11px; color: #8B96AD; letter-spacing: 0.08em; text-transform: uppercase;">CTRL+AI PS-12 Autonomous SRE</span>
  </div>
  <div style="display: flex; align-items: center; gap: 10px;">
    {mode_pill}
    {phase_chip}
    <span class="chip chip-system mono">{inc_id}</span>
  </div>
</div>
"""


def render_alert_card(S: Dict[str, Any]) -> str:
    """Render full-width alert banner with severity, active pulse animation, and elapsed timer."""
    incident = S.get("incident")
    if not incident:
        return """
<div class="mc-card" style="border-left: 4px solid #22C55E; display: flex; align-items: center; justify-content: space-between; padding: 12px 18px;">
  <div style="display: flex; align-items: center; gap: 12px;">
    <span class="chip chip-healthy">HEALTHY</span>
    <span style="font-size: 14px; color: #CBD5E1;">All four microservices operating inside SLA thresholds (error < 0.5%, p99 < 150ms).</span>
  </div>
  <span class="mono" style="font-size: 12px; color: #8B96AD;">STANDBY MODE</span>
</div>
"""

    severity = incident.get("severity", "CRITICAL")
    alert_text = incident.get("alert", "Anomaly detected in production cluster.")
    started_at = incident.get("started_at", time.time())
    is_active = S.get("phase") not in ("RESOLVED", "ESCALATED")

    elapsed_str = f"{int(time.time() - started_at)}s" if S.get("recovery_seconds") is None else f"{S['recovery_seconds']}s"

    border_col = "#EF4444" if severity == "CRITICAL" else "#F59E0B"
    chip_class = "chip-critical" if severity == "CRITICAL" else "chip-amber"

    dot_html = '<span class="pulse-dot"></span>' if is_active else ''

    return f"""
<div class="mc-card" style="border-left: 4px solid {border_col}; display: flex; align-items: center; justify-content: space-between; padding: 14px 18px;">
  <div style="display: flex; align-items: center; gap: 14px;">
    {dot_html}
    <span class="chip {chip_class}">{severity}</span>
    <span style="font-size: 14px; font-weight: 500; color: #F1F5F9;">{alert_text}</span>
  </div>
  <div style="display: flex; align-items: center; gap: 8px;">
    <span class="mc-header-label" style="margin: 0;">ELAPSED</span>
    <span class="mono" style="font-size: 14px; font-weight: 700; color: #38BDF8;">{elapsed_str}</span>
  </div>
</div>
"""


def render_hypothesis_board(S: Dict[str, Any]) -> str:
    """Render the 2-3 competing root cause hypotheses with status chips and evidence."""
    hyps = S.get("hypotheses", [])
    if not hyps:
        return """
<div class="mc-card" style="min-height: 280px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center;">
  <div class="mc-header-label">COMPETING ROOT-CAUSE HYPOTHESIS BOARD</div>
  <p style="font-size: 13px; color: #8B96AD; margin-top: 8px;">Awaiting agent diagnostic telemetry to formulate competing hypotheses.</p>
</div>
"""

    cards_html = []
    for h in hyps:
        status = h.get("status", "open")
        cause = h.get("cause", "")
        conf = float(h.get("confidence", 0.0))
        evidence = h.get("evidence", "")

        conf_pct = int(conf * 100)
        card_class = f"hyp-card {status}"

        status_chips = {
            "open": '<span class="chip chip-amber">OPEN</span>',
            "confirmed": '<span class="chip chip-healthy">CONFIRMED</span>',
            "eliminated": '<span class="chip chip-system">ELIMINATED</span>',
        }
        status_html = status_chips.get(status, f'<span class="chip">{status}</span>')

        cards_html.append(f"""
<div class="{card_class}">
  <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px;">
    <span style="font-size: 13px; font-weight: 600; color: #F1F5F9;">{cause}</span>
    {status_html}
  </div>
  <div style="display: flex; justify-content: space-between; font-size: 11px; color: #8B96AD;" class="mono">
    <span>CONFIDENCE</span>
    <span>{conf_pct}%</span>
  </div>
  <div class="confidence-track">
    <div class="confidence-fill" style="width: {conf_pct}%;"></div>
  </div>
  <div style="font-size: 11px; color: #94A3B8; margin-top: 6px;" class="mono">
    <span style="color: #64748B;">EVIDENCE:</span> {evidence}
  </div>
</div>
""")

    return f"""
<div class="mc-card" style="min-height: 280px;">
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
    <span class="mc-header-label">COMPETING ROOT-CAUSE HYPOTHESES</span>
    <span class="mono" style="font-size: 11px; color: #8B96AD;">{len(hyps)} ACTIVE</span>
  </div>
  {"".join(cards_html)}
</div>
"""


def render_timeline(S: Dict[str, Any]) -> str:
    """Render vertical chronological action timeline with actor and safety tier chips."""
    timeline = S.get("timeline", [])
    if not timeline:
        return """
<div class="mc-card">
  <div class="mc-header-label">INVESTIGATION & REMEDIATION TIMELINE</div>
  <div style="color: #8B96AD; font-size: 13px; padding: 12px 0;">No actions recorded yet. Trigger a scenario to begin investigation.</div>
</div>
"""

    tier_classes = {
        "read": "chip-healthy",
        "reversible": "chip-agent",
        "approval": "chip-amber",
        "blocked": "chip-critical",
        "info": "chip-system",
    }

    actor_classes = {
        "agent": "chip-agent",
        "human": "chip-human",
        "system": "chip-system",
    }

    rows = []
    for item in timeline:
        t = item.get("t", "")
        actor = item.get("actor", "system")
        text = item.get("text", "")
        tier = item.get("tier", "read")

        row_extra = ""
        if tier == "blocked":
            row_extra = "blocked"
        elif tier == "approval":
            row_extra = "approval"

        tier_chip = f'<span class="chip {tier_classes.get(tier, "chip-system")}">{tier.upper()}</span>'
        actor_chip = f'<span class="chip {actor_classes.get(actor, "chip-system")}">{actor.upper()}</span>'

        rows.append(f"""
<div class="timeline-row {row_extra}">
  <div style="display: flex; align-items: center; gap: 10px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
    <span class="mono" style="color: #64748B; font-size: 11px;">{t}</span>
    {actor_chip}
    <span style="color: #E2E8F0; font-size: 12px; font-weight: 500;">{text}</span>
  </div>
  <div style="margin-left: 12px; flex-shrink: 0;">
    {tier_chip}
  </div>
</div>
""")

    return f"""
<div class="mc-card">
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
    <span class="mc-header-label">INVESTIGATION & REMEDIATION TIMELINE</span>
    <span class="mono" style="font-size: 11px; color: #8B96AD;">{len(timeline)} EVENTS</span>
  </div>
  <div class="timeline-container">
    {"".join(rows)}
  </div>
</div>
"""


def render_approval_card(S: Dict[str, Any]) -> str:
    """Render human supervisor approval card when phase is AWAITING_APPROVAL."""
    pending = S.get("pending") or {}
    tool = pending.get("tool", "rollback_config")
    args = pending.get("args", {})
    reason = pending.get("reason", "Production configuration mutation requires supervisor approval.")
    risk = pending.get("risk", "Pod restart and connection string reconfiguration.")

    # Retrieve highest confidence hypothesis
    top_cause = "Missing DATABASE_URL configuration"
    confidence = "98%"
    for h in S.get("hypotheses", []):
        if h.get("status") == "confirmed":
            top_cause = h.get("cause", top_cause)
            confidence = f"{int(h.get('confidence', 0.98) * 100)}%"
            break

    return f"""
<div class="mc-card" style="border: 2px solid #F59E0B; background: rgba(245, 158, 11, 0.06);">
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
    <div style="display: flex; align-items: center; gap: 8px;">
      <span class="chip chip-amber">HUMAN APPROVAL REQUIRED</span>
      <span style="font-size: 14px; font-weight: 700; color: #FBBF24;">Code Gate Enforcing Human Authorization</span>
    </div>
    <span class="chip chip-amber mono">{tool}</span>
  </div>
  <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; font-size: 12px; margin-bottom: 14px;">
    <div class="mc-card-raised">
      <div class="mc-header-label">DIAGNOSED CAUSE & CONFIDENCE</div>
      <div style="font-weight: 600; color: #F1F5F9;">{top_cause}</div>
      <div class="mono" style="color: #38BDF8; margin-top: 4px;">Confidence: {confidence}</div>
    </div>
    <div class="mc-card-raised">
      <div class="mc-header-label">PROPOSED ACTION</div>
      <div style="font-weight: 600; color: #F1F5F9;">{tool} {args}</div>
      <div class="mono" style="color: #F87171; margin-top: 4px;">Risk: {risk}</div>
    </div>
  </div>
  <div class="mc-card-raised" style="font-size: 12px; margin-bottom: 8px;">
    <div class="mc-header-label">SAFETY & ROLLBACK JUSTIFICATION</div>
    <div style="color: #CBD5E1;">{reason}</div>
    <div class="mono" style="color: #94A3B8; margin-top: 6px;">Rollback of rollback: Re-deploy candidate build v2.4.1 from registry. Verification: 3 consecutive passes (error < 2%, latency < 300ms).</div>
  </div>
</div>
"""


def render_escalation_card(S: Dict[str, Any]) -> str:
    """Render structured human escalation packet when incident is ESCALATED."""
    packet = S.get("escalation_packet", {})
    summary = packet.get("summary", "Automated remediation halted.")
    evidence = packet.get("evidence", "Policy restriction or database corruption.")
    rec = packet.get("recommended_next_step", "Manual DBA triage.")
    blocked = packet.get("blocked_actions", ["repair_database (Blocked by code policy)"])

    return f"""
<div class="mc-card" style="border: 2px solid #EF4444; background: rgba(239, 68, 68, 0.05);">
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
    <div style="display: flex; align-items: center; gap: 8px;">
      <span class="chip chip-critical">ESCALATED TO HUMAN ON-CALL</span>
      <span style="font-size: 14px; font-weight: 700; color: #F87171;">Automated Repair Prohibited by Policy</span>
    </div>
    <span class="chip chip-critical mono">{packet.get('incident_id', 'INC-409')}</span>
  </div>
  <div style="font-size: 13px; color: #F1F5F9; margin-bottom: 12px;">
    <strong>Summary:</strong> {summary}
  </div>
  <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; font-size: 12px; margin-bottom: 12px;">
    <div class="mc-card-raised">
      <div class="mc-header-label">TELEMETRY EVIDENCE</div>
      <div class="mono" style="color: #E2E8F0;">{evidence}</div>
    </div>
    <div class="mc-card-raised">
      <div class="mc-header-label">BLOCKED ACTIONS (GATE ENFORCED)</div>
      <div class="mono" style="color: #F87171;">{', '.join(blocked) if blocked else 'repair_database'}</div>
    </div>
  </div>
  <div class="mc-card-raised" style="font-size: 12px;">
    <div class="mc-header-label">RECOMMENDED SUPERVISED NEXT STEPS</div>
    <div class="mono" style="white-space: pre-line; color: #38BDF8;">{rec}</div>
  </div>
</div>
"""


def render_resolved_banner(S: Dict[str, Any]) -> str:
    """Render verified recovery banner with measured recovery time."""
    recovery_sec = S.get("recovery_seconds", 0.0)
    incident = S.get("incident") or {}
    inc_id = incident.get("id", "INCIDENT")

    return f"""
<div class="mc-card" style="border: 2px solid #22C55E; background: rgba(34, 197, 94, 0.06); text-align: center; padding: 20px;">
  <div style="display: flex; justify-content: center; align-items: center; gap: 10px; margin-bottom: 8px;">
    <span class="chip chip-healthy">INCIDENT RESOLVED</span>
    <span class="chip chip-healthy mono">{inc_id}</span>
  </div>
  <div class="mono" style="font-size: 32px; font-weight: 700; color: #4ADE80; margin: 10px 0;">
    {recovery_sec}s
  </div>
  <div style="font-size: 13px; color: #94A3B8;">
    Verified across 3 consecutive criteria passes (error < 2%, p99 < 300ms, queue < 20, DB integrity ok). Postmortem archived to memory.
  </div>
</div>
"""


def render_memory_comparison_chart(S: Dict[str, Any]) -> Optional[go.Figure]:
    """Generate minimal Plotly first-vs-repeat recovery comparison chart."""
    comp = get_memory_comparison(S)
    if not comp:
        return None

    categories = ["Recovery Time (s)", "Diagnostic & Action Steps"]
    first_vals = [comp["first_seconds"], comp["first_steps"]]
    repeat_vals = [comp["repeat_seconds"], comp["repeat_steps"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name=f"First ({comp['first_id']})",
        x=categories,
        y=first_vals,
        marker_color="#F59E0B",
    ))
    fig.add_trace(go.Bar(
        name=f"Repeat ({comp['repeat_id']} via Memory)",
        x=categories,
        y=repeat_vals,
        marker_color="#22C55E",
    ))

    fig.update_layout(
        title=f"Incident Memory Acceleration: {comp['time_savings_pct']}% Faster Recovery",
        barmode="group",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color="#E6EAF2", size=12),
        margin=dict(l=20, r=20, t=40, b=20),
        height=220,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis=dict(gridcolor="#1E273D", zerolinecolor="#1E273D"),
        xaxis=dict(gridcolor="#1E273D"),
    )
    return fig
