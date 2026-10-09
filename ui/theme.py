"""Theme tokens, custom typography, and CSS injection for Mission Control UI."""

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

:root {
  --bg: #0B0F17;
  --surface: #121826;
  --raised: #182033;
  --border: #25304A;
  --text: #E6EAF2;
  --muted: #8B96AD;
  --healthy: #22C55E;
  --amber: #F59E0B;
  --critical: #EF4444;
  --agent: #38BDF8;
  --human: #A78BFA;
  --system: #94A3B8;
}

/* Hide Streamlit default chrome */
#MainMenu, header, footer, .stDeployButton {
  display: none !important;
}

body, .stApp {
  background-color: var(--bg) !important;
  color: var(--text) !important;
  font-family: 'Inter', sans-serif !important;
}

.mono {
  font-family: 'JetBrains Mono', monospace !important;
}

/* Base card styling */
.mc-card {
  background-color: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.25);
  margin-bottom: 16px;
}

.mc-card-raised {
  background-color: var(--raised);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 14px;
  margin-bottom: 12px;
}

.mc-header-label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--muted);
  font-weight: 600;
  margin-bottom: 6px;
}

/* Status chips with 12% tint */
.chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
  font-family: 'JetBrains Mono', monospace;
  letter-spacing: 0.02em;
}

.chip-healthy {
  background: rgba(34, 197, 94, 0.12);
  border: 1px solid rgba(34, 197, 94, 0.5);
  color: #4ADE80;
}

.chip-amber {
  background: rgba(245, 158, 11, 0.12);
  border: 1px solid rgba(245, 158, 11, 0.5);
  color: #FBBF24;
}

.chip-critical {
  background: rgba(239, 68, 68, 0.12);
  border: 1px solid rgba(239, 68, 68, 0.5);
  color: #F87171;
}

.chip-agent {
  background: rgba(56, 189, 248, 0.12);
  border: 1px solid rgba(56, 189, 248, 0.5);
  color: #38BDF8;
}

.chip-human {
  background: rgba(167, 139, 250, 0.12);
  border: 1px solid rgba(167, 139, 250, 0.5);
  color: #C4B5FD;
}

.chip-system {
  background: rgba(148, 163, 184, 0.12);
  border: 1px solid rgba(148, 163, 184, 0.5);
  color: #CBD5E1;
}

/* Pulsing dot animation */
@keyframes pulseGlow {
  0% { transform: scale(0.95); opacity: 0.6; box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); }
  70% { transform: scale(1.1); opacity: 1; box-shadow: 0 0 0 8px rgba(239, 68, 68, 0); }
  100% { transform: scale(0.95); opacity: 0.6; box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
}

.pulse-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  background-color: var(--critical);
  border-radius: 50%;
  animation: pulseGlow 2s infinite;
}

/* Timeline scroll container */
.timeline-container {
  max-height: 380px;
  overflow-y: auto;
  padding-right: 6px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.timeline-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background-color: #121826;
  border: 1px solid #1E273D;
  border-radius: 8px;
  font-size: 13px;
}

.timeline-row.blocked {
  background: rgba(239, 68, 68, 0.08);
  border-color: rgba(239, 68, 68, 0.4);
}

.timeline-row.approval {
  background: rgba(245, 158, 11, 0.08);
  border-color: rgba(245, 158, 11, 0.4);
}

/* Confidence bar */
.confidence-track {
  width: 100%;
  height: 6px;
  background-color: #1E273D;
  border-radius: 3px;
  overflow: hidden;
  margin: 6px 0;
}

.confidence-fill {
  height: 100%;
  background: linear-gradient(90deg, #38BDF8, #22C55E);
  border-radius: 3px;
  transition: width 0.4s ease;
}

/* Hypothesis cards */
.hyp-card {
  background-color: var(--raised);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 12px;
  margin-bottom: 8px;
  transition: all 0.3s ease;
}

.hyp-card.confirmed {
  border-color: var(--healthy);
  background: rgba(34, 197, 94, 0.06);
}

.hyp-card.eliminated {
  opacity: 0.55;
  text-decoration: line-through;
  border-color: #1E273D;
}

/* Button overrides */
.stButton > button {
  min-height: 44px;
  border-radius: 8px !important;
  font-weight: 600 !important;
  font-family: 'Inter', sans-serif !important;
  transition: all 0.2s ease !important;
}
</style>
"""
