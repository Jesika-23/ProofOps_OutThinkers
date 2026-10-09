"""Tests for core/memory.py."""

from core.state import init_state
from core.faults import inject_cache_outage
from core.sandbox import apply_restart_cache
from core.verifier import verify_recovery
from core.tools import execute_tool
from core.memory import build_signature, find_similar_incident, get_memory_comparison


def test_signature_and_find_similar():
    S = init_state()
    inject_cache_outage(S)
    sig = build_signature(S)
    assert "cache_unreachable" in sig

    # Initially empty memory
    assert find_similar_incident(S, sig) is None

    # Resolve incident
    apply_restart_cache(S)
    verify_recovery(S, delay_sec=0)
    execute_tool(S, "resolve_incident", {"summary": "Fixed cache"})

    # Now similar incident should be found
    match = find_similar_incident(S, sig)
    assert match is not None
    assert match["id"] == "INC-101"
    assert "restart_cache" in match["runbook"]


def test_memory_comparison():
    S = init_state()

    # Record first incident
    inject_cache_outage(S)
    apply_restart_cache(S)
    verify_recovery(S, delay_sec=0)
    S["recovery_seconds"] = 35.0
    execute_tool(S, "resolve_incident", {"summary": "First cache outage"})

    # Record repeat incident
    inject_cache_outage(S, is_repeat=True)
    apply_restart_cache(S)
    verify_recovery(S, delay_sec=0)
    S["recovery_seconds"] = 12.0
    execute_tool(S, "resolve_incident", {"summary": "Repeat cache outage"})

    comp = get_memory_comparison(S)
    assert comp is not None
    assert comp["has_repeat"] is True
    assert comp["first_seconds"] == 35.0
    assert comp["repeat_seconds"] == 12.0
    assert comp["time_savings_pct"] > 0
