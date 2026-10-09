"""Safety gate and tool execution policy for AutoHeal EvidenceFirst.
Safety is strictly enforced in CODE, never only in the prompt.
Unknown tools are blocked.
"""

from typing import Any, Dict

# Code-enforced tool risk classification
TOOL_TIERS: Dict[str, str] = {
    # Read-only tier
    "get_alert": "read",
    "get_topology": "read",
    "query_logs": "read",
    "get_metrics": "read",
    "check_health": "read",
    "ping_dependency": "read",
    "diff_config": "read",
    "get_recent_deployments": "read",
    "find_similar_incident": "read",
    "verify_recovery": "read",
    "update_hypotheses": "read",
    "page_human": "read",
    "resolve_incident": "read",
    # Reversible tier
    "restart_cache": "reversible",
    # Approval tier
    "rollback_config": "approval",
    # Blocked tier (exposed to model on purpose to verify gate enforcement)
    "repair_database": "blocked",
}

# Tools that are UI/screen only and do NOT count towards diagnostic limit
NON_DIAGNOSTIC_TOOLS = {"update_hypotheses", "page_human", "resolve_incident", "verify_recovery"}


def get_tool_tier(tool_name: str) -> str:
    """Return the safety tier for a given tool name. Unknown tools default to 'blocked'."""
    return TOOL_TIERS.get(tool_name, "blocked")


def is_diagnostic_tool(tool_name: str) -> bool:
    """Determine whether a tool counts towards the 5-call diagnostic limit."""
    tier = get_tool_tier(tool_name)
    return tier == "read" and tool_name not in NON_DIAGNOSTIC_TOOLS
