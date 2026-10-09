"""Tests for core/faults.py."""

from core.state import init_state
from core.faults import inject_cache_outage, inject_bad_config, inject_db_integrity


def test_inject_cache_outage():
    S = init_state()
    inject_cache_outage(S)
    assert S["phase"] == "INVESTIGATING"
    assert S["incident"]["id"] == "INC-101"
    assert S["services"]["cache"]["status"] == "down"
    assert S["services"]["cache"]["reachable"] is False
    assert S["services"]["worker"]["status"] == "degraded"
    assert S["services"]["worker"]["queue_depth"] == 380
    assert S["services"]["orders_api"]["status"] == "down"
    assert S["services"]["orders_api"]["error_rate"] == 48.0
    assert S["services"]["orders_api"]["latency_ms"] == 2400
    assert S["services"]["database"]["status"] == "healthy"


def test_inject_bad_config():
    S = init_state()
    inject_bad_config(S)
    assert S["incident"]["id"] == "INC-204"
    assert S["services"]["orders_api"]["status"] == "down"
    assert S["services"]["orders_api"]["error_rate"] == 100.0
    assert "DATABASE_URL" not in S["config"]["current"]
    assert "DATABASE_URL" in S["config"]["previous"]
    assert S["deployments"][0]["version"] == "v2.4.1"


def test_inject_db_integrity():
    S = init_state()
    inject_db_integrity(S)
    assert S["incident"]["id"] == "INC-409"
    assert S["services"]["database"]["status"] == "degraded"
    assert S["services"]["database"]["integrity"] == "checksum_mismatch"
    assert S["services"]["orders_api"]["error_rate"] == 22.0
