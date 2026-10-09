"""Human escalation packet generator for AutoHeal EvidenceFirst."""

from typing import Any, Dict, List
import copy
from core.sandbox import query_logs


def build_escalation_packet(
    S: Dict[str, Any],
    summary: str = "",
    evidence: str = "",
    recommended_next_step: str = "",
) -> Dict[str, Any]:
    """Assemble a comprehensive evidence packet for human incident responder.

    Includes:
    - Incident identity & severity
    - Timeline of actions taken
    - Service health snapshot
    - Diagnostic logs
    - Current hypotheses board state
    - Tests / diagnostics performed
    - Blocked automated actions
    - Recommended supervised next steps
    """
    incident = S.get("incident") or {}

    # Extract tests run from timeline
    tests_run = [
        item["text"]
        for item in S.get("timeline", [])
        if item.get("kind") in ("diagnostic", "action") and item.get("tier") == "read"
    ]

    # Extract blocked actions
    blocked_actions = [
        item["text"]
        for item in S.get("timeline", [])
        if item.get("tier") == "blocked"
    ]

    # Relevant logs from affected services
    logs_snapshot = {}
    for svc_name, svc_data in S.get("services", {}).items():
        if svc_data.get("status") != "healthy":
            logs_snapshot[svc_name] = query_logs(S, svc_name, minutes=15)
    if not logs_snapshot:
        logs_snapshot["orders_api"] = query_logs(S, "orders_api", minutes=15)

    default_rec = (
        "1. Isolate replica db-shard-02 from read pool.\n"
        "2. Run offline table verification `pg_checksums -D /var/lib/postgresql/data`.\n"
        "3. Initiate point-in-time recovery (PITR) from snapshot snap-db-wal-048 if checksum mismatch is confirmed."
    )

    return {
        "incident_id": incident.get("id", "INC-UNKNOWN"),
        "severity": incident.get("severity", "CRITICAL"),
        "alert": incident.get("alert", "Unspecified alert"),
        "summary": summary or "System requires human operator intervention due to high-risk fault condition.",
        "evidence": evidence or "Automated recovery blocked by policy or integrity failure detected.",
        "recommended_next_step": recommended_next_step or default_rec,
        "services_health": copy.deepcopy(S.get("services", {})),
        "hypotheses": copy.deepcopy(S.get("hypotheses", [])),
        "tests_run": tests_run,
        "blocked_actions": blocked_actions,
        "logs_snapshot": logs_snapshot,
        "timeline": copy.deepcopy(S.get("timeline", [])),
    }
