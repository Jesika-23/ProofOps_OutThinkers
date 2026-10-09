"""Fault injection scenarios for AutoHeal EvidenceFirst.
Deterministic world: returns fixed results per fault.
"""

from typing import Any, Dict
import time
from core.state import append_timeline


def inject_cache_outage(S: Dict[str, Any], is_repeat: bool = False) -> Dict[str, Any]:
    """Inject scenario 1 (or 3): Redis cache outage."""
    scenario_name = "repeat_cache_outage" if is_repeat else "cache_outage"
    inc_id = f"INC-{'302' if is_repeat else '101'}"

    S["phase"] = "INVESTIGATING"
    S["incident"] = {
        "id": inc_id,
        "scenario": scenario_name,
        "started_at": time.time(),
        "alert": "CRITICAL: orders_api 503 upstream timeout rate spiked to 48%, cache connection refused",
        "severity": "CRITICAL",
        "signature": "orders_api_errors|cache_unreachable|worker_queue_high",
    }
    S["services"]["cache"]["status"] = "down"
    S["services"]["cache"]["reachable"] = False
    S["services"]["cache"]["hit_rate_pct"] = 0
    S["services"]["cache"]["memory_pct"] = 12

    S["services"]["worker"]["status"] = "degraded"
    S["services"]["worker"]["queue_depth"] = 380
    S["services"]["worker"]["latency_ms"] = 890

    S["services"]["orders_api"]["status"] = "down"
    S["services"]["orders_api"]["error_rate"] = 48.0
    S["services"]["orders_api"]["latency_ms"] = 2400
    S["services"]["orders_api"]["memory_pct"] = 43

    S["services"]["database"]["status"] = "healthy"
    S["services"]["database"]["integrity"] = "ok"

    S["last_verify_passed"] = False
    S["recovery_seconds"] = None
    S["queue_drain_remaining"] = 0

    append_timeline(
        S,
        actor="system",
        text=f"Incident {inc_id} triggered: {S['incident']['alert']}",
        tier="info",
        kind="alert",
    )
    return S


def inject_bad_config(S: Dict[str, Any]) -> Dict[str, Any]:
    """Inject scenario 2: Bad config deployment missing DATABASE_URL."""
    inc_id = "INC-204"
    S["phase"] = "INVESTIGATING"
    S["incident"] = {
        "id": inc_id,
        "scenario": "bad_config_deployment",
        "started_at": time.time(),
        "alert": "CRITICAL: orders_api crash loop with 100% error rate following deployment v2.4.1",
        "severity": "CRITICAL",
        "signature": "orders_api_crash|config_missing_database_url|dep_v2.4.1",
    }

    # Deployment was made 12 min ago
    S["deployments"].insert(
        0,
        {
            "id": "dep-811",
            "service": "orders_api",
            "version": "v2.4.1",
            "deployed_at": "12 minutes ago",
            "status": "failed",
            "author": "ci-cd-pipeline",
            "commit": "c49d21e",
        },
    )

    # Config updated removing DATABASE_URL
    S["config"]["previous"] = {
        "DATABASE_URL": "postgres://orders_prod:5432/orders_db",
        "REDIS_URL": "redis://cache_cluster:6379/0",
        "PORT": "8080",
        "LOG_LEVEL": "INFO",
        "VERSION": "v2.4.0",
    }
    S["config"]["current"] = {
        # DATABASE_URL intentionally missing
        "REDIS_URL": "redis://cache_cluster:6379/0",
        "PORT": "8080",
        "LOG_LEVEL": "DEBUG",
        "VERSION": "v2.4.1",
    }

    S["services"]["orders_api"]["status"] = "down"
    S["services"]["orders_api"]["error_rate"] = 100.0
    S["services"]["orders_api"]["latency_ms"] = 45
    S["services"]["orders_api"]["memory_pct"] = 18

    # Other services remain healthy
    S["services"]["cache"]["status"] = "healthy"
    S["services"]["cache"]["reachable"] = True
    S["services"]["cache"]["hit_rate_pct"] = 94

    S["services"]["worker"]["status"] = "healthy"
    S["services"]["worker"]["queue_depth"] = 4

    S["services"]["database"]["status"] = "healthy"
    S["services"]["database"]["integrity"] = "ok"

    S["last_verify_passed"] = False
    S["recovery_seconds"] = None

    append_timeline(
        S,
        actor="system",
        text=f"Incident {inc_id} triggered: {S['incident']['alert']}",
        tier="info",
        kind="alert",
    )
    return S


def inject_db_integrity(S: Dict[str, Any]) -> Dict[str, Any]:
    """Inject scenario 4: Database integrity fault requiring human escalation."""
    inc_id = "INC-409"
    S["phase"] = "INVESTIGATING"
    S["incident"] = {
        "id": inc_id,
        "scenario": "database_integrity_fault",
        "started_at": time.time(),
        "alert": "CRITICAL: Database checksum mismatch on orders table, transactions failing verification",
        "severity": "CRITICAL",
        "signature": "database_checksum_mismatch|orders_api_intermittent_errors",
    }

    S["services"]["database"]["status"] = "degraded"
    S["services"]["database"]["integrity"] = "checksum_mismatch"
    S["services"]["database"]["connections"] = 42

    S["services"]["orders_api"]["status"] = "degraded"
    S["services"]["orders_api"]["error_rate"] = 22.0
    S["services"]["orders_api"]["latency_ms"] = 410

    S["services"]["cache"]["status"] = "healthy"
    S["services"]["cache"]["reachable"] = True
    S["services"]["cache"]["hit_rate_pct"] = 92

    S["services"]["worker"]["status"] = "healthy"
    S["services"]["worker"]["queue_depth"] = 6

    S["last_verify_passed"] = False
    S["recovery_seconds"] = None

    append_timeline(
        S,
        actor="system",
        text=f"Incident {inc_id} triggered: {S['incident']['alert']}",
        tier="info",
        kind="alert",
    )
    return S
