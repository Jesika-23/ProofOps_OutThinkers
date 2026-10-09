"""Tests for core/state.py."""

from core.state import init_state, reset_environment, append_timeline


def test_init_state_structure():
    S = init_state()
    assert S["phase"] == "IDLE"
    assert S["incident"] is None
    assert S["hypotheses"] == []
    assert S["timeline"] == []
    assert S["contents"] == []
    assert S["pending"] is None
    assert S["memory"] == []
    assert S["llm_calls"] == 0
    assert S["mode"] == "gemini"
    assert S["mode_reason"] == ""
    assert S["diag_calls"] == 0
    assert S["recovery_seconds"] is None
    assert S["last_verify_passed"] is None

    # Check services
    assert set(S["services"].keys()) == {"orders_api", "worker", "cache", "database"}
    assert S["services"]["orders_api"]["error_rate"] == 0.3
    assert S["services"]["orders_api"]["latency_ms"] == 120
    assert S["services"]["cache"]["reachable"] is True
    assert S["services"]["database"]["integrity"] == "ok"


def test_reset_environment_preserves_memory_and_llm_calls():
    S = init_state()
    S["incident"] = {"id": "INC-999", "alert": "test"}
    S["llm_calls"] = 7
    S["memory"] = [{"id": "INC-101", "root_cause": "cache"}]
    S["hypotheses"] = [{"cause": "cache", "confidence": 0.8}]
    S["diag_calls"] = 4
    S["recovery_seconds"] = 45.2

    reset_environment(S)

    assert S["phase"] == "IDLE"
    assert S["incident"] is None
    assert S["hypotheses"] == []
    assert S["diag_calls"] == 0
    assert S["recovery_seconds"] is None

    # Memory and llm_calls must NOT be cleared!
    assert S["llm_calls"] == 7
    assert len(S["memory"]) == 1
    assert S["memory"][0]["id"] == "INC-101"


def test_append_timeline():
    S = init_state()
    append_timeline(S, actor="agent", text="Ran ping", tier="read")
    assert len(S["timeline"]) == 1
    assert S["timeline"][0]["actor"] == "agent"
    assert S["timeline"][0]["tier"] == "read"
    assert S["timeline"][0]["text"] == "Ran ping"
