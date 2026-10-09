"""Tests for core/guardrails.py."""

from core.guardrails import get_tool_tier, is_diagnostic_tool


def test_tool_tiers():
    assert get_tool_tier("get_alert") == "read"
    assert get_tool_tier("query_logs") == "read"
    assert get_tool_tier("restart_cache") == "reversible"
    assert get_tool_tier("rollback_config") == "approval"
    assert get_tool_tier("repair_database") == "blocked"
    # Unknown tools must be blocked!
    assert get_tool_tier("drop_tables") == "blocked"
    assert get_tool_tier("rm_rf") == "blocked"


def test_diagnostic_tool_counter():
    assert is_diagnostic_tool("query_logs") is True
    assert is_diagnostic_tool("get_metrics") is True
    assert is_diagnostic_tool("check_health") is True
    # update_hypotheses and terminal tools are NOT diagnostic
    assert is_diagnostic_tool("update_hypotheses") is False
    assert is_diagnostic_tool("page_human") is False
    assert is_diagnostic_tool("resolve_incident") is False
    assert is_diagnostic_tool("restart_cache") is False
