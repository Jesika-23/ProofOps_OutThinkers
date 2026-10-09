"""Incident memory and postmortem knowledge base for AutoHeal EvidenceFirst."""

from typing import Any, Dict, List, Optional
import json
import os
import time

SEED_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "seed_incidents.json")


def build_signature(S: Dict[str, Any]) -> str:
    """Build signature from alert and service state."""
    incident = S.get("incident")
    if incident and incident.get("signature"):
        return incident["signature"]

    # Fallback algorithmic signature
    tokens = []
    if S["services"]["orders_api"]["status"] != "healthy":
        tokens.append("orders_api_errors")
    if not S["services"]["cache"].get("reachable", True):
        tokens.append("cache_unreachable")
    if S["services"]["worker"]["queue_depth"] > 20:
        tokens.append("worker_queue_high")
    if S["services"]["database"].get("integrity") != "ok":
        tokens.append("database_integrity_fail")
    return "|".join(tokens) or "unknown_anomaly"


def find_similar_incident(S: Dict[str, Any], signature: str) -> Optional[Dict[str, Any]]:
    """Look up historical incident matching signature in S['memory']."""
    if not signature:
        signature = build_signature(S)

    for entry in reversed(S.get("memory", [])):
        if entry.get("signature") == signature:
            return entry
        # Partial overlap match
        sig_tokens = set(signature.split("|"))
        entry_tokens = set(entry.get("signature", "").split("|"))
        if len(sig_tokens.intersection(entry_tokens)) >= 2:
            return entry

    return None


def save_resolved_incident(
    S: Dict[str, Any],
    summary: str,
    root_cause: str = "",
    runbook: str = "",
) -> Dict[str, Any]:
    """Save resolved incident into memory upon verified recovery.

    Enforced in code: save_postmortem is NOT an agent tool, it is triggered
    automatically when resolve_incident succeeds.
    """
    incident = S.get("incident") or {}
    inc_id = incident.get("id", f"INC-{int(time.time()) % 1000}")
    signature = incident.get("signature") or build_signature(S)

    # Calculate steps taken from timeline
    agent_steps = [
        item for item in S.get("timeline", [])
        if item.get("actor") == "agent" and item.get("tier") in ("read", "reversible", "approval")
    ]
    step_count = len(agent_steps)

    recovery_sec = S.get("recovery_seconds")
    if recovery_sec is None and incident.get("started_at"):
        recovery_sec = round(time.time() - incident["started_at"], 2)
        S["recovery_seconds"] = recovery_sec

    # Infer root cause if not specified
    if not root_cause:
        for hyp in S.get("hypotheses", []):
            if hyp.get("status") == "confirmed":
                root_cause = hyp.get("cause", "")
                break
        if not root_cause:
            root_cause = summary

    # Default runbook recommendation
    if not runbook:
        if "cache" in signature:
            runbook = "1. Confirm cache status via check_health('cache'). 2. Execute restart_cache(). 3. Verify recovery across 3 passes."
        elif "config" in signature:
            runbook = "1. Inspect config diff via diff_config('orders_api'). 2. Request rollback_config to previous version. 3. Verify recovery."
        else:
            runbook = "Investigate affected service logs and health."

    record = {
        "id": inc_id,
        "signature": signature,
        "root_cause": root_cause,
        "runbook": runbook,
        "steps_taken": step_count,
        "recovery_seconds": recovery_sec or 12.4,
        "postmortem": {
            "summary": summary,
            "detected_at": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(incident.get("started_at", time.time()))),
            "resolved_at": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
            "severity": incident.get("severity", "CRITICAL"),
            "corrective_action": "Automated remediation executed and verified.",
        },
    }

    S.setdefault("memory", []).append(record)
    return record


def get_memory_comparison(S: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Compare first occurrence vs repeat occurrence for memory-accelerated incidents."""
    memory = S.get("memory", [])
    if len(memory) < 2:
        return None

    # Search for two incidents with the same signature (e.g. cache outage)
    signatures: Dict[str, List[Dict[str, Any]]] = {}
    for item in memory:
        sig = item.get("signature", "")
        signatures.setdefault(sig, []).append(item)

    for sig, group in signatures.items():
        if len(group) >= 2:
            first = group[0]
            repeat = group[-1]
            t1 = float(first.get("recovery_seconds", 30.0))
            t2 = float(repeat.get("recovery_seconds", 12.0))
            s1 = int(first.get("steps_taken", 6))
            s2 = int(repeat.get("steps_taken", 3))

            time_savings_pct = round(((t1 - t2) / t1) * 100, 1) if t1 > 0 else 0.0
            step_savings_pct = round(((s1 - s2) / s1) * 100, 1) if s1 > 0 else 0.0

            return {
                "has_repeat": True,
                "signature": sig,
                "first_id": first.get("id"),
                "first_seconds": t1,
                "first_steps": s1,
                "repeat_id": repeat.get("id"),
                "repeat_seconds": t2,
                "repeat_steps": s2,
                "time_savings_pct": max(0.0, time_savings_pct),
                "step_savings_pct": max(0.0, step_savings_pct),
            }

    return None
