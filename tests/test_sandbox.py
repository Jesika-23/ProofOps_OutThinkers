"""Tests for core/sandbox.py."""

from core.state import init_state
from core.faults import inject_cache_outage, inject_bad_config
from core.sandbox import (
    get_metrics,
    check_health,
    ping,
    query_logs,
    apply_restart_cache,
    apply_rollback,
)


def test_get_metrics_and_health():
    S = init_state()
    m = get_metrics(S, "orders_api")
    assert m["service"] == "orders_api"
    assert m["status"] == "healthy"

    h = check_health(S, "cache")
    assert h["healthy"] is True
    assert h["reachable"] is True


def test_ping_dependencies():
    S = init_state()
    res = ping(S, "orders_api", "cache")
    assert res["connected"] is True

    # Invalidate cache
    inject_cache_outage(S)
    res_failed = ping(S, "orders_api", "cache")
    assert res_failed["connected"] is False
    assert "unreachable" in res_failed["error"]


def test_query_logs_scenario_specific():
    S = init_state()
    inject_cache_outage(S)
    logs = query_logs(S, "cache")
    assert any("connection refused" in line or "SIGSEGV" in line for line in logs)

    inject_bad_config(S)
    api_logs = query_logs(S, "orders_api")
    assert any("DATABASE_URL" in line for line in api_logs)


def test_apply_restart_cache():
    S = init_state()
    inject_cache_outage(S)
    assert S["services"]["cache"]["reachable"] is False

    res = apply_restart_cache(S)
    assert res["success"] is True
    assert S["services"]["cache"]["reachable"] is True
    assert S["services"]["cache"]["status"] == "healthy"
    assert S["services"]["orders_api"]["status"] == "healthy"
    assert S["services"]["worker"]["queue_depth"] <= 20


def test_apply_rollback():
    S = init_state()
    inject_bad_config(S)
    assert S["services"]["orders_api"]["error_rate"] == 100.0

    res = apply_rollback(S, "v2.4.0")
    assert res["success"] is True
    assert S["config"]["current"]["VERSION"] == "v2.4.0"
    assert "DATABASE_URL" in S["config"]["current"]
    assert S["services"]["orders_api"]["status"] == "healthy"
    assert S["services"]["orders_api"]["error_rate"] == 0.3
