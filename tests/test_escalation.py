"""Tests for core/escalation.py."""

from core.state import init_state
from core.faults import inject_db_integrity
from core.tools import execute_tool
from core.escalation import build_escalation_packet


def test_build_escalation_packet():
    S = init_state()
    inject_db_integrity(S)
    execute_tool(S, "repair_database", {"table": "orders"})  # will be blocked

    packet = build_escalation_packet(
        S,
        summary="Checksum mismatch detected on orders table",
        evidence="Integrity checks failing, automated repair blocked by policy",
        recommended_next_step="Supervised WAL replay check",
    )

    assert packet["incident_id"] == "INC-409"
    assert packet["severity"] == "CRITICAL"
    assert "Checksum mismatch" in packet["summary"]
    assert any("repair_database" in b for b in packet["blocked_actions"])
    assert "orders_api" in packet["services_health"]
    assert packet["services_health"]["database"]["integrity"] == "checksum_mismatch"
