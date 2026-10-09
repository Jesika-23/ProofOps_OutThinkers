"""Tests for core/fallback.py."""

from core.state import init_state
from core.faults import inject_cache_outage, inject_bad_config, inject_db_integrity
from core.fallback import run_fallback_step
from core.agent import resume_after_approval


def test_fallback_cache_outage_resolves():
    S = init_state()
    inject_cache_outage(S)
    res = run_fallback_step(S)
    assert res["status"] == "resolved"
    assert S["phase"] == "RESOLVED"
    assert S["services"]["cache"]["status"] == "healthy"
    assert S["services"]["orders_api"]["status"] == "healthy"
    assert S["last_verify_passed"] is True
    assert len(S["hypotheses"]) >= 2
    assert len(S["memory"]) == 1


def test_fallback_bad_config_approval_pause_and_resume():
    S = init_state()
    inject_bad_config(S)

    # First run must pause awaiting approval!
    res = run_fallback_step(S)
    assert res["status"] == "awaiting_approval"
    assert S["phase"] == "AWAITING_APPROVAL"
    assert S["pending"] is not None
    assert S["services"]["orders_api"]["error_rate"] == 100.0  # NOT yet modified!

    # Human approves
    res_resume = resume_after_approval(S, client=None, approved=True)
    assert res_resume["status"] == "resolved"
    assert S["phase"] == "RESOLVED"
    assert S["services"]["orders_api"]["status"] == "healthy"
    assert S["last_verify_passed"] is True


def test_fallback_bad_config_rejected():
    S = init_state()
    inject_bad_config(S)
    run_fallback_step(S)

    # Human rejects
    res_reject = resume_after_approval(S, client=None, approved=False)
    assert res_reject["status"] == "escalated"
    assert S["phase"] == "ESCALATED"
    assert S["pending"] is None


def test_fallback_db_integrity_escalates():
    S = init_state()
    inject_db_integrity(S)
    res = run_fallback_step(S)
    assert res["status"] == "escalated"
    assert S["phase"] == "ESCALATED"
    # Blocked action must be recorded
    assert any(t["tier"] == "blocked" for t in S["timeline"])
    assert "escalation_packet" in S


def test_fallback_repeat_cache_accelerated():
    S = init_state()
    # 1. Resolve first cache incident
    inject_cache_outage(S)
    run_fallback_step(S)
    first_steps = len(S["timeline"])

    # 2. Reset environment and inject repeat cache
    from core.state import reset_environment
    reset_environment(S)
    inject_cache_outage(S, is_repeat=True)

    # 3. Fallback should find memory match and accelerate
    res = run_fallback_step(S)
    assert res["status"] == "resolved_via_memory"
    repeat_steps = len(S["timeline"])
    assert repeat_steps < first_steps
