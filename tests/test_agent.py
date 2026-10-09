"""Tests for core/agent.py using mocked Gemini client."""

from unittest.mock import MagicMock
from google.genai import types
from core.state import init_state
from core.faults import inject_cache_outage, inject_bad_config
from core.agent import run_agent, resume_after_approval, CALL_LIMIT


def _make_mock_response(function_name: str, args: dict, extra_calls: list = None):
    parts = [types.Part.from_function_call(name=function_name, args=args)]
    if extra_calls:
        for ex in extra_calls:
            parts.append(types.Part.from_function_call(name=ex["name"], args=ex.get("args", {})))
    content = types.Content(role="model", parts=parts)
    candidate = MagicMock()
    candidate.content = content
    resp = MagicMock()
    resp.candidates = [candidate]
    return resp


def test_agent_skips_extra_parallel_calls():
    S = init_state()
    inject_cache_outage(S)

    # Return 2 function calls in one response
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = [
        _make_mock_response("get_metrics", {"service": "orders_api"}, extra_calls=[{"name": "check_health", "args": {"service": "database"}}]),
        _make_mock_response("page_human", {"summary": "test", "evidence": "test", "recommended_next_step": "test"}),
    ]

    res = run_agent(S, client=mock_client)
    assert res["status"] == "escalated"
    # Verify that skipped response was recorded
    last_user_content = S["contents"][-1] if S["contents"] else None
    assert any(hasattr(p, "function_response") for p in S["contents"][-2].parts)


def test_agent_pauses_on_approval_and_resumes():
    S = init_state()
    inject_bad_config(S)

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = [
        _make_mock_response("rollback_config", {"service": "orders_api", "to_version": "v2.4.0"}),
        _make_mock_response("verify_recovery", {}),
        _make_mock_response("resolve_incident", {"summary": "Resolved after rollback"}),
    ]

    res = run_agent(S, client=mock_client)
    assert res["status"] == "awaiting_approval"
    assert S["phase"] == "AWAITING_APPROVAL"
    assert S["pending"] is not None

    # Resume after approval
    res_resume = resume_after_approval(S, client=mock_client, approved=True)
    assert res_resume["status"] == "resolved"
    assert S["phase"] == "RESOLVED"
    assert S["pending"] is None


def test_agent_call_limit_switches_to_fallback():
    S = init_state()
    inject_cache_outage(S)
    S["llm_calls"] = CALL_LIMIT  # 30

    mock_client = MagicMock()
    run_agent(S, client=mock_client)
    assert S["mode"] == "fallback"
    assert "limit" in S["mode_reason"]
    # Fallback should have completed the incident
    assert S["phase"] == "RESOLVED"


def test_agent_api_error_retries_and_falls_back():
    S = init_state()
    inject_cache_outage(S)

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("429 ResourceExhausted: rate limit exceeded")

    run_agent(S, client=mock_client)
    assert S["mode"] == "fallback"
    assert "API error" in S["mode_reason"]
    # Incident resolved via reliable fallback policy
    assert S["phase"] == "RESOLVED"
