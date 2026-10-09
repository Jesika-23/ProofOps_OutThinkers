"""Tool definitions, execution dispatcher, and Gemini schemas for AutoHeal EvidenceFirst.
Safety gate is strictly code-enforced.
"""

from typing import Any, Dict, List, Optional
import copy
import time
from core.guardrails import get_tool_tier, is_diagnostic_tool
from core.sandbox import (
    get_metrics,
    check_health,
    ping,
    query_logs,
    apply_restart_cache,
    apply_rollback,
)
from core.verifier import verify_recovery
from core.memory import find_similar_incident, save_resolved_incident
from core.escalation import build_escalation_packet
from core.state import append_timeline


def diff_config(S: Dict[str, Any], service: str = "orders_api") -> Dict[str, Any]:
    """Inspect differences between current active config and previous stable config."""
    cfg = S.get("config", {})
    current = cfg.get("current", {})
    previous = cfg.get("previous", {})

    diff_lines = []
    # Keys missing in current
    for k, v in previous.items():
        if k not in current:
            diff_lines.append(f"- {k}={v} (REMOVED in current)")
        elif current[k] != v:
            diff_lines.append(f"~ {k}: changed from '{v}' to '{current[k]}'")
    for k, v in current.items():
        if k not in previous:
            diff_lines.append(f"+ {k}={v} (ADDED in current)")

    return {
        "service": service,
        "current_version": current.get("VERSION", "unknown"),
        "previous_version": previous.get("VERSION", "unknown"),
        "differences": diff_lines,
        "has_divergence": len(diff_lines) > 0,
    }


def execute_tool(
    S: Dict[str, Any],
    name: str,
    args: Optional[Dict[str, Any]] = None,
    approved: bool = False,
) -> Dict[str, Any]:
    """Execute a tool through the code-enforced safety gate.

    - Unknown tools are BLOCKED.
    - Blocked tier tools are rejected immediately.
    - Approval tier tools pause and return approval_required unless approved=True.
    - Every call is recorded in S['timeline'] with its tier.
    """
    args = args or {}
    tier = get_tool_tier(name)

    # 1. Blocked tier (or unknown tool)
    if tier == "blocked":
        msg = f"Tool '{name}' is BLOCKED by code-enforced safety gate: Automated database repair or unauthorized commands are prohibited."
        append_timeline(S, actor="agent", text=f"Attempted blocked tool '{name}': {msg}", tier="blocked", kind="blocked")
        return {"status": "blocked", "message": msg}

    # 2. Approval tier (when not yet approved)
    if tier == "approval" and not approved:
        pending_info = {
            "tool": name,
            "args": args,
            "reason": "Modifying production deployment or rolling back config requires human supervisor approval.",
            "risk": "Rollback will restart orders_api service and revert environment bindings.",
            "to_version": args.get("to_version", "v2.4.0"),
        }
        S["pending"] = pending_info
        S["phase"] = "AWAITING_APPROVAL"
        append_timeline(
            S,
            actor="agent",
            text=f"Requested approval for '{name}' with args {args}. Pausing for human review.",
            tier="approval",
            kind="approval_request",
        )
        return {
            "status": "approval_required",
            "tool": name,
            "args": args,
            "reason": pending_info["reason"],
            "risk": pending_info["risk"],
        }

    # Count diagnostic calls
    if is_diagnostic_tool(name):
        S["diag_calls"] = S.get("diag_calls", 0) + 1

    # 3. Read tier executions
    if name == "get_alert":
        inc = S.get("incident")
        result = inc if inc else {"status": "No active incident"}
        append_timeline(S, actor="agent", text="Queried active incident alert", tier="read", kind="diagnostic")
        return result

    elif name == "get_topology":
        topo = {
            "services": ["orders_api", "worker", "cache", "database"],
            "dependencies": {
                "orders_api": ["cache", "database", "worker"],
                "worker": ["cache"],
                "cache": [],
                "database": [],
            },
        }
        append_timeline(S, actor="agent", text="Retrieved service topology graph", tier="read", kind="diagnostic")
        return topo

    elif name == "query_logs":
        svc = args.get("service", "orders_api")
        minutes = int(args.get("minutes", 15))
        logs = query_logs(S, svc, minutes)
        append_timeline(S, actor="agent", text=f"Queried logs for '{svc}' (past {minutes}m)", tier="read", kind="diagnostic")
        return {"service": svc, "lines": logs}

    elif name == "get_metrics":
        svc = args.get("service", "orders_api")
        metrics = get_metrics(S, svc)
        append_timeline(S, actor="agent", text=f"Queried metrics for '{svc}'", tier="read", kind="diagnostic")
        return metrics

    elif name == "check_health":
        svc = args.get("service", "orders_api")
        health = check_health(S, svc)
        append_timeline(S, actor="agent", text=f"Checked health of '{svc}'", tier="read", kind="diagnostic")
        return health

    elif name == "ping_dependency":
        f_svc = args.get("from_service", "orders_api")
        t_svc = args.get("to_service", "cache")
        res = ping(S, f_svc, t_svc)
        append_timeline(S, actor="agent", text=f"Pinged {f_svc} -> {t_svc}: {'OK' if res.get('connected') else 'FAILED'}", tier="read", kind="diagnostic")
        return res

    elif name == "diff_config":
        svc = args.get("service", "orders_api")
        res = diff_config(S, svc)
        append_timeline(S, actor="agent", text=f"Checked config diff for '{svc}'", tier="read", kind="diagnostic")
        return res

    elif name == "get_recent_deployments":
        deps = S.get("deployments", [])
        append_timeline(S, actor="agent", text=f"Queried recent deployments (count: {len(deps)})", tier="read", kind="diagnostic")
        return {"deployments": deps}

    elif name == "find_similar_incident":
        sig = args.get("signature", "")
        match = find_similar_incident(S, sig)
        append_timeline(S, actor="agent", text=f"Queried incident memory for signature '{sig}'", tier="read", kind="diagnostic")
        return {"found": match is not None, "match": match}

    elif name == "verify_recovery":
        # Run 3 consecutive checks
        res = verify_recovery(S, delay_sec=0)
        return res

    elif name == "update_hypotheses":
        # Screen-only: does not count as diagnostic
        hyps = args.get("hypotheses", [])
        S["hypotheses"] = hyps
        append_timeline(S, actor="agent", text=f"Updated root-cause hypothesis board ({len(hyps)} hypotheses)", tier="read", kind="screen")
        return {"status": "updated", "count": len(hyps)}

    elif name == "page_human":
        summary = args.get("summary", "Human assistance required")
        evidence = args.get("evidence", "")
        recommended = args.get("recommended_next_step", "")
        packet = build_escalation_packet(S, summary, evidence, recommended)
        S["phase"] = "ESCALATED"
        S["escalation_packet"] = packet
        append_timeline(S, actor="agent", text=f"Paged human on-call: {summary}", tier="read", kind="escalation")
        return {"status": "escalated", "packet": packet}

    elif name == "resolve_incident":
        summary = args.get("summary", "Incident resolved")
        # CODE-ENFORCED: Accepted ONLY if the last verify_recovery passed!
        if S.get("last_verify_passed") is not True:
            msg = "REJECTED by safety gate: verify_recovery has not passed or was not run. Run verify_recovery before resolving."
            append_timeline(S, actor="agent", text=f"Attempted resolve_incident without passed verification: {msg}", tier="read", kind="rejected")
            return {"status": "rejected", "message": msg}

        S["phase"] = "RESOLVED"
        incident = S.get("incident") or {}
        if S.get("recovery_seconds") is None and incident.get("started_at"):
            S["recovery_seconds"] = round(time.time() - incident["started_at"], 2)

        # Code automatically generates & saves postmortem upon verified resolve
        record = save_resolved_incident(S, summary=summary)
        append_timeline(S, actor="agent", text=f"Incident RESOLVED: {summary} (Recovery time: {S.get('recovery_seconds', 0)}s)", tier="read", kind="resolution")
        return {
            "status": "resolved",
            "recovery_seconds": S.get("recovery_seconds"),
            "postmortem_id": record["id"],
            "message": "Incident successfully resolved and recorded in incident memory.",
        }

    # 4. Reversible tier
    elif name == "restart_cache":
        res = apply_restart_cache(S)
        S["phase"] = "REMEDIATING"
        return res

    # 5. Approved approval tier
    elif name == "rollback_config":
        to_version = args.get("to_version", "v2.4.0")
        res = apply_rollback(S, to_version=to_version)
        S["pending"] = None
        S["phase"] = "REMEDIATING"
        return res

    return {"status": "unknown_tool", "message": f"Tool '{name}' not found."}


# Gemini Tool Declarations
TOOL_DECLARATIONS = [
    {
        "name": "get_alert",
        "description": "Retrieve current active incident alert, severity, and start timestamp.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
        },
    },
    {
        "name": "get_topology",
        "description": "Retrieve service architecture graph and inter-service dependency links.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
        },
    },
    {
        "name": "query_logs",
        "description": "Query recent timestamped log lines for a specific service.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "service": {
                    "type": "STRING",
                    "description": "Name of service to inspect: orders_api, worker, cache, or database",
                },
                "minutes": {
                    "type": "INTEGER",
                    "description": "Window of logs to inspect in minutes (e.g. 15)",
                },
            },
            "required": ["service"],
        },
    },
    {
        "name": "get_metrics",
        "description": "Retrieve real-time metrics (error rate, latency, memory, queue depth) for a service.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "service": {
                    "type": "STRING",
                    "description": "Name of service: orders_api, worker, cache, or database",
                },
            },
            "required": ["service"],
        },
    },
    {
        "name": "check_health",
        "description": "Perform health check probe on a service.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "service": {
                    "type": "STRING",
                    "description": "Name of service to check",
                },
            },
            "required": ["service"],
        },
    },
    {
        "name": "ping_dependency",
        "description": "Test TCP/HTTP connectivity and latency between two services.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "from_service": {
                    "type": "STRING",
                    "description": "Calling service (e.g. orders_api)",
                },
                "to_service": {
                    "type": "STRING",
                    "description": "Target service (e.g. cache)",
                },
            },
            "required": ["from_service", "to_service"],
        },
    },
    {
        "name": "diff_config",
        "description": "Inspect environment variable and version differences between current and previous deployment.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "service": {
                    "type": "STRING",
                    "description": "Service name to diff config for (default orders_api)",
                },
            },
        },
    },
    {
        "name": "get_recent_deployments",
        "description": "Retrieve recent CI/CD deployments history and commit metadata.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
        },
    },
    {
        "name": "find_similar_incident",
        "description": "Query incident memory for historical postmortems matching the symptom signature.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "signature": {
                    "type": "STRING",
                    "description": "Incident symptom signature to match",
                },
            },
        },
    },
    {
        "name": "update_hypotheses",
        "description": "Maintain 2-3 competing root-cause hypotheses on the visible mission control board.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "hypotheses": {
                    "type": "ARRAY",
                    "description": "List of competing hypotheses",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "cause": {"type": "STRING", "description": "Hypothesized root cause"},
                            "confidence": {"type": "NUMBER", "description": "Confidence score 0.0 to 1.0"},
                            "status": {"type": "STRING", "description": "open, eliminated, or confirmed"},
                            "evidence": {"type": "STRING", "description": "Observed evidence supporting or refuting this"},
                        },
                        "required": ["cause", "confidence", "status", "evidence"],
                    },
                },
            },
            "required": ["hypotheses"],
        },
    },
    {
        "name": "restart_cache",
        "description": "Safely restart the Redis cache cluster (Reversible tier action).",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
        },
    },
    {
        "name": "rollback_config",
        "description": "Rollback service configuration and deployment to a previous known-good version (Requires Human Approval).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "service": {
                    "type": "STRING",
                    "description": "Service to rollback (orders_api)",
                },
                "to_version": {
                    "type": "STRING",
                    "description": "Target version to rollback to (e.g. v2.4.0)",
                },
            },
            "required": ["service", "to_version"],
        },
    },
    {
        "name": "repair_database",
        "description": "Attempt automated direct repair or checksum fix on database tables (BLOCKED BY POLICY).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "table": {
                    "type": "STRING",
                    "description": "Database table name",
                },
            },
        },
    },
    {
        "name": "verify_recovery",
        "description": "Run 3 consecutive verification passes to validate latency, error rate, queue depth, and integrity.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
        },
    },
    {
        "name": "resolve_incident",
        "description": "Mark the incident as resolved. Strictly accepted ONLY if verify_recovery has previously passed.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "summary": {
                    "type": "STRING",
                    "description": "Brief summary of root cause and successful remediation",
                },
            },
            "required": ["summary"],
        },
    },
    {
        "name": "page_human",
        "description": "Escalate the incident to a human on-call engineer with an assembled evidence packet.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "summary": {
                    "type": "STRING",
                    "description": "Incident summary and justification for human escalation",
                },
                "evidence": {
                    "type": "STRING",
                    "description": "Key diagnostic evidence showing why automation cannot proceed",
                },
                "recommended_next_step": {
                    "type": "STRING",
                    "description": "Recommended supervised operational steps for the engineer",
                },
            },
            "required": ["summary", "evidence", "recommended_next_step"],
        },
    },
]
