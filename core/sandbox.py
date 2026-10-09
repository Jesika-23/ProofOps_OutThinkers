"""Simulator sandbox for AutoHeal EvidenceFirst.
Deterministic service behavior with +/-1% cosmetic noise on healthy metrics.
"""

from typing import Any, Dict, List
import copy
import time
from core.state import append_timeline


def _add_cosmetic_noise(val: float, seed_offset: int = 0) -> float:
    """Add +/-1% deterministic cosmetic variation to healthy metrics based on time."""
    # Deterministic variation cycle: -1.0% to +1.0% without unbounded randomness
    cycle = ((int(time.time() * 2) + seed_offset) % 5) - 2  # -2, -1, 0, 1, 2
    delta = val * (cycle * 0.005)  # +/- 1% max
    return round(val + delta, 2)


def get_metrics(S: Dict[str, Any], service: str) -> Dict[str, Any]:
    """Retrieve current operational metrics for a specific service."""
    if service not in S["services"]:
        return {"error": f"Unknown service '{service}'. Valid services: {list(S['services'].keys())}"}

    svc = copy.deepcopy(S["services"][service])
    # Apply minor cosmetic noise if service is healthy
    if svc["status"] == "healthy":
        if "latency_ms" in svc:
            svc["latency_ms"] = int(_add_cosmetic_noise(svc["latency_ms"], 1))
        if "memory_pct" in svc:
            svc["memory_pct"] = int(_add_cosmetic_noise(svc["memory_pct"], 2))

    return {
        "service": service,
        "status": svc["status"],
        "metrics": svc,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def check_health(S: Dict[str, Any], service: str) -> Dict[str, Any]:
    """Perform health checks on a specific service."""
    if service not in S["services"]:
        return {"error": f"Unknown service '{service}'"}

    svc = S["services"][service]
    is_healthy = svc["status"] == "healthy"
    details = {
        "service": service,
        "status": svc["status"],
        "healthy": is_healthy,
    }

    if service == "cache":
        details["reachable"] = svc.get("reachable", True)
        details["hit_rate_pct"] = svc.get("hit_rate_pct", 94)
    elif service == "database":
        details["integrity"] = svc.get("integrity", "ok")
        details["connections"] = svc.get("connections", 18)
    elif service == "orders_api":
        details["error_rate_pct"] = svc.get("error_rate", 0.3)
        details["latency_ms"] = svc.get("latency_ms", 120)
    elif service == "worker":
        details["queue_depth"] = svc.get("queue_depth", 4)

    return details


def ping(S: Dict[str, Any], from_service: str, to_service: str) -> Dict[str, Any]:
    """Test network latency and connectivity from one service to another."""
    valid_services = {"orders_api", "worker", "cache", "database"}
    if from_service not in valid_services or to_service not in valid_services:
        return {"error": f"Invalid service in ping({from_service}, {to_service})"}

    # Cache connectivity check
    if to_service == "cache" and not S["services"]["cache"].get("reachable", True):
        return {
            "from": from_service,
            "to": to_service,
            "connected": False,
            "latency_ms": None,
            "error": "Connection refused (port 6379): host unreachable",
        }

    # Orders API down check
    if to_service == "orders_api" and S["services"]["orders_api"]["status"] == "down":
        if S["services"]["orders_api"]["error_rate"] >= 100.0:
            return {
                "from": from_service,
                "to": to_service,
                "connected": False,
                "latency_ms": None,
                "error": "HTTP 502 Bad Gateway / Connection reset by peer",
            }

    return {
        "from": from_service,
        "to": to_service,
        "connected": True,
        "latency_ms": 1.4 if (from_service, to_service) == ("orders_api", "cache") else 2.8,
        "status": "OK",
    }


def query_logs(S: Dict[str, Any], service: str, minutes: int = 15) -> List[str]:
    """Return realistic timestamped log lines for a service under current state."""
    now = time.strftime("%H:%M:%S")
    incident = S.get("incident")
    scenario = incident["scenario"] if incident else None

    if service == "cache":
        if not S["services"]["cache"].get("reachable", True):
            return [
                f"{now} [redis-server] FATAL: received SIGSEGV in background saving thread",
                f"{now} [redis-server] CRITICAL: process terminated with exit status 139",
                f"{now} [systemd] redis.service: Main process exited, code=killed, status=11/SEGV",
                f"{now} [healthcheck] ERROR cache unreachable: connection refused (port 6379)",
            ]
        return [
            f"{now} [redis-server] Ready to accept connections tcp",
            f"{now} [redis-server] 14 clients connected, memory usage 55%",
            f"{now} [redis-server] Cache hit rate: 94.2% across 84,200 operations",
        ]

    elif service == "worker":
        if S["services"]["worker"]["status"] == "degraded":
            queue_val = S["services"]["worker"]["queue_depth"]
            return [
                f"{now} [worker-pool] WARN worker queue growing rapidly (queue_depth={queue_val})",
                f"{now} [worker-pool] ERROR redis cache connection failed: connect ECONNREFUSED 10.0.4.12:6379",
                f"{now} [worker-pool] WARN retry backoff exponential tier 4 reached",
                f"{now} [worker-pool] WARN order fulfillment tasks waiting on cache lock",
            ]
        return [
            f"{now} [worker-pool] Processed 128 queue items in 4.2s (queue_depth={S['services']['worker']['queue_depth']})",
            f"{now} [worker-pool] Worker healthy, heartbeat ACK",
        ]

    elif service == "orders_api":
        if scenario == "bad_config_deployment":
            return [
                f"{now} [orders_api] Starting orders_api v2.4.1 ...",
                f"{now} [config] Initializing environment bindings",
                f"{now} [config] ERROR missing required env DATABASE_URL",
                f"{now} [bootstrap] FATAL orders_api failed to start: panic: empty DATABASE_URL",
                f"{now} [orchestrator] Container orders_api restartCount=12 (CrashLoopBackOff)",
            ]
        elif scenario in ("cache_outage", "repeat_cache_outage"):
            return [
                f"{now} [orders_api] ERROR cache unreachable: connection refused",
                f"{now} [orders_api] WARN fallback to direct DB read exhausted pool",
                f"{now} [orders_api] ERROR orders_api 503 upstream timeout (latency 2400ms)",
                f"{now} [orders_api] Ingress error rate spiked to 48.0%",
            ]
        elif scenario == "database_integrity_fault":
            return [
                f"{now} [orders_api] ERROR database query failed on order validation",
                f"{now} [orders_api] CRITICAL transaction integrity check failure (500)",
                f"{now} [orders_api] 22% of checkout requests aborted due to integrity guardrail",
            ]
        return [
            f"{now} [orders_api] GET /healthz 200 OK (0.8ms)",
            f"{now} [orders_api] POST /v1/orders 201 Created (118ms)",
            f"{now} [orders_api] Ingress error rate: 0.3%, throughput: 420 rps",
        ]

    elif service == "database":
        if S["services"]["database"].get("integrity") == "checksum_mismatch":
            return [
                f"{now} [postgres] CRITICAL checksum mismatch on orders table (block 849201)",
                f"{now} [postgres] CRITICAL transaction integrity validation failed",
                f"{now} [postgres] ERROR row count verification inconsistent across primary index",
                f"{now} [storage-engine] WARN possible corrupted block encountered during WAL replay",
            ]
        return [
            f"{now} [postgres] LOG: checkpoint complete: wrote 42 buffers (0.1%)",
            f"{now} [postgres] Active connections: 18/100, replication lag: 0ms",
            f"{now} [postgres] Database integrity check: OK",
        ]

    return [f"{now} [{service}] service operating normally"]


def tick(S: Dict[str, Any]) -> None:
    """Advance simulated world time by one tick."""
    S["tick_count"] += 1
    # Handle worker queue drain if cache was restarted
    if S.get("queue_drain_remaining", 0) > 0:
        S["queue_drain_remaining"] -= 1
        current_q = S["services"]["worker"]["queue_depth"]
        if S["queue_drain_remaining"] == 2:
            S["services"]["worker"]["queue_depth"] = 140
        elif S["queue_drain_remaining"] == 1:
            S["services"]["worker"]["queue_depth"] = 18
        else:
            S["services"]["worker"]["queue_depth"] = 4
            S["services"]["worker"]["status"] = "healthy"
            S["services"]["worker"]["latency_ms"] = 35


def apply_restart_cache(S: Dict[str, Any]) -> Dict[str, Any]:
    """Execute cache service restart (Reversible tier fix)."""
    S["services"]["cache"]["status"] = "healthy"
    S["services"]["cache"]["reachable"] = True
    S["services"]["cache"]["hit_rate_pct"] = 94
    S["services"]["cache"]["memory_pct"] = 55

    # Orders API recovers immediately once cache is reachable
    S["services"]["orders_api"]["status"] = "healthy"
    S["services"]["orders_api"]["error_rate"] = 0.3
    S["services"]["orders_api"]["latency_ms"] = 120

    # Worker queue drains over 2-3 ticks
    S["queue_drain_remaining"] = 3
    # Immediately trigger ticks to simulate draining
    tick(S)  # tick 1 -> 140
    tick(S)  # tick 2 -> 18
    tick(S)  # tick 3 -> 4, healthy

    snapshot_id = f"snap-cache-restart-{int(time.time()) % 10000}"
    append_timeline(
        S,
        actor="agent",
        text=f"Executed restart_cache: Redis service restarted successfully [{snapshot_id}]",
        tier="reversible",
        kind="remediation",
    )
    return {
        "success": True,
        "snapshot_id": snapshot_id,
        "message": "Cache service restarted successfully and verified reachable.",
    }


def apply_rollback(S: Dict[str, Any], to_version: str = "v2.4.0") -> Dict[str, Any]:
    """Execute configuration rollback (Approval tier fix)."""
    # Restore configuration
    prev_config = S["config"].get("previous", {})
    if not prev_config:
        prev_config = {
            "DATABASE_URL": "postgres://orders_prod:5432/orders_db",
            "REDIS_URL": "redis://cache_cluster:6379/0",
            "PORT": "8080",
            "LOG_LEVEL": "INFO",
            "VERSION": to_version,
        }

    S["config"]["current"] = copy.deepcopy(prev_config)
    S["config"]["current"]["VERSION"] = to_version

    # Restore orders_api
    S["services"]["orders_api"]["status"] = "healthy"
    S["services"]["orders_api"]["error_rate"] = 0.3
    S["services"]["orders_api"]["latency_ms"] = 120
    S["services"]["orders_api"]["memory_pct"] = 41

    # Record deployment rollback
    S["deployments"].insert(
        0,
        {
            "id": f"dep-rollback-{int(time.time()) % 1000}",
            "service": "orders_api",
            "version": to_version,
            "deployed_at": "just now",
            "status": "active",
            "author": "autoheal-agent",
            "commit": "rollback-target",
        },
    )

    snapshot_id = f"snap-rollback-{to_version}-{int(time.time()) % 10000}"
    append_timeline(
        S,
        actor="agent",
        text=f"Executed rollback_config to {to_version} [{snapshot_id}]",
        tier="approval",
        kind="remediation",
    )
    return {
        "success": True,
        "snapshot_id": snapshot_id,
        "message": f"Successfully rolled back orders_api configuration to {to_version}.",
    }
