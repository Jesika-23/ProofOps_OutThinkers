"""Shared application state S for AutoHeal EvidenceFirst.
Pure Python dict operations, testable without a browser or Streamlit.
"""

from typing import Any, Dict, List, Optional
import copy
import time

HEALTHY_SERVICES = {
    "orders_api": {
        "status": "healthy",
        "error_rate": 0.3,
        "latency_ms": 120,
        "memory_pct": 41,
    },
    "worker": {
        "status": "healthy",
        "queue_depth": 4,
        "latency_ms": 35,
        "memory_pct": 32,
    },
    "cache": {
        "status": "healthy",
        "reachable": True,
        "hit_rate_pct": 94,
        "memory_pct": 55,
    },
    "database": {
        "status": "healthy",
        "connections": 18,
        "max_connections": 100,
        "integrity": "ok",
        "memory_pct": 62,
    },
}

HEALTHY_CONFIG = {
    "current": {
        "DATABASE_URL": "postgres://orders_prod:5432/orders_db",
        "REDIS_URL": "redis://cache_cluster:6379/0",
        "PORT": "8080",
        "LOG_LEVEL": "INFO",
        "VERSION": "v2.4.0",
    },
    "previous": {
        "DATABASE_URL": "postgres://orders_prod:5432/orders_db",
        "REDIS_URL": "redis://cache_cluster:6379/0",
        "PORT": "8080",
        "LOG_LEVEL": "INFO",
        "VERSION": "v2.4.0",
    },
}

BASELINE_DEPLOYMENTS = [
    {
        "id": "dep-810",
        "service": "orders_api",
        "version": "v2.4.0",
        "deployed_at": "3 hours ago",
        "status": "active",
        "author": "release-bot",
        "commit": "a1f94c2",
    },
    {
        "id": "dep-798",
        "service": "worker",
        "version": "v1.9.2",
        "deployed_at": "1 day ago",
        "status": "active",
        "author": "platform-team",
        "commit": "8c41d01",
    },
]


def init_state() -> Dict[str, Any]:
    """Initialize a fresh AutoHeal state dictionary S."""
    return {
        "phase": "IDLE",  # IDLE | INVESTIGATING | AWAITING_APPROVAL | REMEDIATING | VERIFYING | RESOLVED | ESCALATED
        "services": copy.deepcopy(HEALTHY_SERVICES),
        "config": copy.deepcopy(HEALTHY_CONFIG),
        "deployments": copy.deepcopy(BASELINE_DEPLOYMENTS),
        "incident": None,  # None or {id, scenario, started_at, alert, severity, signature}
        "hypotheses": [],  # list of {cause, confidence, status, evidence}
        "timeline": [],  # list of {t, actor, kind, text, tier}
        "contents": [],  # Gemini message history
        "pending": None,  # None or {tool, args, reason, risk}
        "memory": [],  # resolved incidents
        "llm_calls": 0,
        "mode": "gemini",  # "gemini" | "fallback"
        "mode_reason": "",
        "diag_calls": 0,
        "recovery_seconds": None,
        "last_verify_passed": None,
        "tick_count": 0,
        "queue_drain_remaining": 0,
    }


def reset_environment(S: Dict[str, Any]) -> Dict[str, Any]:
    """Restore healthy baseline, clearing incident data but preserving memory and llm_calls."""
    S["phase"] = "IDLE"
    S["services"] = copy.deepcopy(HEALTHY_SERVICES)
    S["config"] = copy.deepcopy(HEALTHY_CONFIG)
    S["deployments"] = copy.deepcopy(BASELINE_DEPLOYMENTS)
    S["incident"] = None
    S["hypotheses"] = []
    S["timeline"] = []
    S["contents"] = []
    S["pending"] = None
    S["diag_calls"] = 0
    S["recovery_seconds"] = None
    S["last_verify_passed"] = None
    S["tick_count"] = 0
    S["queue_drain_remaining"] = 0
    return S


def append_timeline(
    S: Dict[str, Any],
    actor: str,
    text: str,
    tier: str = "read",
    kind: str = "action",
) -> None:
    """Append a timeline entry to S['timeline'] with simulated timestamp."""
    entry = {
        "t": time.strftime("%H:%M:%S"),
        "actor": actor,  # "agent" | "human" | "system"
        "kind": kind,
        "text": text,
        "tier": tier,  # "read" | "reversible" | "approval" | "blocked" | "info"
    }
    S["timeline"].append(entry)
