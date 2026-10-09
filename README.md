# AutoHeal EvidenceFirst
**CTRL+AI Challenge PS-12 Auto-Heal**

An evidence-first incident-response agent for a simulated orders platform with four microservices (`orders_api`, `worker`, `cache`, `database`).

Powered by Google Gemini (Flash-Lite / Flash via the official `google-genai` SDK) or an automated reliable fallback policy. Investigates strictly with read-only tools, maintains 2-3 competing root-cause hypotheses on a mission control board, applies only code-allowed remediation actions, verifies recovery over 3 consecutive health passes, learns from prior incidents, and escalates to a human on-call with a comprehensive evidence packet when safety limits are encountered.

---

## Architecture & Code-Enforced Safety
- **Deterministic Sandbox**: A simulated 4-service cluster with fixed fault behavior and +/-1% cosmetic metric variations.
- **Strict Code Safety Gate (`core/guardrails.py`)**:
  - `READ`: `get_alert`, `get_topology`, `query_logs`, `get_metrics`, `check_health`, `ping_dependency`, `diff_config`, `get_recent_deployments`, `find_similar_incident`, `verify_recovery`, `update_hypotheses`, `page_human`, `resolve_incident`.
  - `REVERSIBLE`: `restart_cache` (executed autonomously).
  - `APPROVAL`: `rollback_config` (pauses and requires supervisor authorization).
  - `BLOCKED`: `repair_database`, arbitrary system shell commands (blocked in Python code, never just prompt).
- **Verification Guarantee**: `resolve_incident` is strictly rejected by code unless 3 consecutive criteria checks pass.
- **Incident Memory**: Postmortems and signatures are automatically recorded. Repeat incidents retrieve past runbooks and execute accelerated confirmation.

---

## Repository Structure
```
app.py                    # Streamlit Mission Control application entry point
ui/
  theme.py                # Design tokens, dark theme CSS, typography
  topology_svg.py         # 4-node inline SVG topology with live status glows
  components.py           # Cards, hypothesis board, timeline, and comparison chart
core/
  state.py                # Pure-Python shared state dict S
  sandbox.py              # Simulator, logs, health checks, metrics
  faults.py               # Deterministic fault scenarios
  verifier.py             # 3-pass consecutive recovery verification
  tools.py                # Tool dispatcher & Gemini function schemas
  guardrails.py           # Code-enforced risk tiers & safety gates
  agent.py                # Gemini orchestration loop & approval resume
  fallback.py             # Deterministic fallback policy
  memory.py               # Incident signatures, memory lookup & comparison
  escalation.py           # Structured human on-call evidence packet
tests/                    # Full pytest suite for all core modules
data/
  seed_incidents.json     # Incident postmortem database
docs/
  demo_script.md          # 4-minute demo walkthrough
requirements.txt          # Python dependencies
```

---

## How to Run

### Local Setup
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. (Optional) Set your Gemini API Key
export GEMINI_API_KEY="your-api-key-here"

# 3. Launch Mission Control
streamlit run app.py
```

### Running Pytest
```bash
pytest
```

### Streamlit Community Cloud Deployment
1. Push repository to GitHub.
2. Link repository in [share.streamlit.io](https://share.streamlit.io).
3. Set main file path to `app.py`.
4. (Optional) Add `GEMINI_API_KEY` and `CHAOS_ACCESS_CODE` in Streamlit App Secrets. If omitted, the app starts safely in **Reliable fallback policy** mode.
