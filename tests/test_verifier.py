"""Tests for core/verifier.py."""

from core.state import init_state
from core.faults import inject_cache_outage
from core.sandbox import apply_restart_cache
from core.verifier import verify_recovery, check_recovery_criteria


def test_recovery_criteria_healthy():
    S = init_state()
    checks = check_recovery_criteria(S)
    assert all(c["passed"] for c in checks)


def test_verify_recovery_fails_during_fault():
    S = init_state()
    inject_cache_outage(S)
    res = verify_recovery(S, delay_sec=0)
    assert res["verified"] is False
    assert S["last_verify_passed"] is False


def test_verify_recovery_passes_after_fix():
    S = init_state()
    inject_cache_outage(S)
    assert verify_recovery(S, delay_sec=0)["verified"] is False

    apply_restart_cache(S)
    res = verify_recovery(S, delay_sec=0)
    assert res["verified"] is True
    assert S["last_verify_passed"] is True
