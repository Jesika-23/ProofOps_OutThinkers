"""Tests for core/tools.py."""

from core.state import init_state
from core.faults import inject_cache_outage, inject_bad_config, inject_db_integrity
from core.tools import execute_tool, diff_config


def test_unknown_and_blocked_tools():
    S = init_state()
    # Unknown tool blocked
    res_unknown = execute_tool(S, "arbitrary_shell_command", {})
    assert res_unknown["status"] == "blocked"

    # repair_database explicitly blocked
    res_blocked = execute_tool(S, "repair_database", {"table": "orders"})
    assert res_blocked["status"] == "blocked"
    assert any(t["tier"] == "blocked" for t in S["timeline"])


def test_approval_tier_flow():
    S = init_state()
    inject_bad_config(S)

    # Without approval: paused and returns approval_required
    res_unapproved = execute_tool(S, "rollback_config", {"service": "orders_api", "to_version": "v2.4.0"})
    assert res_unapproved["status"] == "approval_required"
    assert S["phase"] == "AWAITING_APPROVAL"
    assert S["pending"] is not None
    assert S["services"]["orders_api"]["error_rate"] == 100.0  # NOT yet modified!

    # With approval: executed
    res_approved = execute_tool(S, "rollback_config", {"service": "orders_api", "to_version": "v2.4.0"}, approved=True)
    assert res_approved["success"] is True
    assert S["services"]["orders_api"]["status"] == "healthy"
    assert S["pending"] is None


def test_resolve_incident_requires_verified_recovery():
    S = init_state()
    inject_cache_outage(S)

    # Attempt resolve without verification
    res_bad = execute_tool(S, "resolve_incident", {"summary": "Done"})
    assert res_bad["status"] == "rejected"
    assert S["phase"] != "RESOLVED"

    # Fix and verify
    execute_tool(S, "restart_cache")
    execute_tool(S, "verify_recovery")
    assert S["last_verify_passed"] is True

    # Now resolve succeeds
    res_ok = execute_tool(S, "resolve_incident", {"summary": "Redis cache restarted and verified"})
    assert res_ok["status"] == "resolved"
    assert S["phase"] == "RESOLVED"
    assert len(S["memory"]) == 1


def test_page_human_escalation():
    S = init_state()
    inject_db_integrity(S)
    res = execute_tool(S, "page_human", {
        "summary": "Database checksum mismatch",
        "evidence": "Corruption on orders table",
        "recommended_next_step": "Isolate shard and restore from snapshot",
    })
    assert res["status"] == "escalated"
    assert S["phase"] == "ESCALATED"
    assert "packet" in res


def test_diff_config():
    S = init_state()
    inject_bad_config(S)
    res = diff_config(S, "orders_api")
    assert res["has_divergence"] is True
    assert any("DATABASE_URL" in d for d in res["differences"])
