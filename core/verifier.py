"""Recovery verifier for AutoHeal EvidenceFirst.
Enforces 3 consecutive checks across core health criteria.
"""

from typing import Any, Callable, Dict, List, Optional
import time
from core.state import append_timeline


def check_recovery_criteria(S: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Evaluate current system state against strict recovery thresholds.

    Criteria:
    - orders_api status == "healthy"
    - orders_api error_rate < 2.0%
    - orders_api latency_ms < 300 ms
    - worker queue_depth < 20
    - cache reachable is True
    - database integrity == "ok"
    """
    orders_api = S["services"].get("orders_api", {})
    worker = S["services"].get("worker", {})
    cache = S["services"].get("cache", {})
    database = S["services"].get("database", {})

    api_status = orders_api.get("status", "unknown")
    api_error = orders_api.get("error_rate", 100.0)
    api_latency = orders_api.get("latency_ms", 9999)
    worker_queue = worker.get("queue_depth", 999)
    cache_reachable = cache.get("reachable", False)
    db_integrity = database.get("integrity", "unknown")

    checks = [
        {
            "check": "orders_api_status",
            "required": "healthy",
            "value": api_status,
            "passed": api_status == "healthy",
        },
        {
            "check": "orders_api_error_rate",
            "required": "< 2.0%",
            "value": f"{api_error}%",
            "passed": api_error < 2.0,
        },
        {
            "check": "orders_api_latency",
            "required": "< 300 ms",
            "value": f"{api_latency} ms",
            "passed": api_latency < 300,
        },
        {
            "check": "worker_queue_depth",
            "required": "< 20",
            "value": worker_queue,
            "passed": worker_queue < 20,
        },
        {
            "check": "cache_reachable",
            "required": "True",
            "value": cache_reachable,
            "passed": cache_reachable is True,
        },
        {
            "check": "database_integrity",
            "required": "ok",
            "value": db_integrity,
            "passed": db_integrity == "ok",
        },
    ]
    return checks


def verify_recovery(
    S: Dict[str, Any],
    sleep_fn: Optional[Callable[[float], None]] = None,
    delay_sec: float = 0.05,
) -> Dict[str, Any]:
    """Execute 3 consecutive verification passes.

    Must pass all 3 checks consecutively to qualify as verified recovery.
    Sets S['last_verify_passed'].
    """
    sleep = sleep_fn if sleep_fn is not None else time.sleep

    all_passed = True
    iterations = []

    for i in range(1, 4):
        iteration_checks = check_recovery_criteria(S)
        iteration_passed = all(c["passed"] for c in iteration_checks)
        iterations.append({
            "pass_number": i,
            "passed": iteration_passed,
            "checks": iteration_checks,
        })
        if not iteration_passed:
            all_passed = False
            break
        if i < 3 and delay_sec > 0:
            sleep(delay_sec)

    S["last_verify_passed"] = all_passed
    S["phase"] = "VERIFYING" if not all_passed else S.get("phase", "VERIFYING")

    status_str = "PASSED (3/3 checks)" if all_passed else "FAILED"
    append_timeline(
        S,
        actor="agent",
        text=f"Executed verify_recovery: {status_str}",
        tier="read",
        kind="verification",
    )

    return {
        "verified": all_passed,
        "consecutive_passes": len(iterations) if all_passed else len(iterations) - 1,
        "details": iterations,
    }
