"""Gemini Agent loop and orchestration for AutoHeal EvidenceFirst.
Uses the official google-genai SDK with single MODEL_NAME constant.
Real reasoning, deterministic world, code-enforced safety.
"""

from typing import Any, Callable, Dict, List, Optional
import time
import copy
from core.guardrails import is_diagnostic_tool
from core.tools import execute_tool, TOOL_DECLARATIONS
from core.fallback import run_fallback_step
from core.memory import find_similar_incident, build_signature

# NOTE: Confirm the exact current Flash-Lite name in Google AI Studio
# e.g., "gemini-2.5-flash-lite", "gemini-2.0-flash-lite", or "gemini-2.5-flash"
MODEL_NAME = "gemini-2.5-flash-lite"

MAX_TURNS = 12
CALL_LIMIT = 30

SYSTEM_PROMPT = (
    "You are AutoHeal, an evidence-first incident-response agent for a simulated orders platform. "
    "Rules: 1) Begin with read-only checks; never choose a fix before you have evidence. "
    "2) Keep 2 to 3 competing root-cause hypotheses on the board; call update_hypotheses after every tool result. "
    "3) Mark a hypothesis eliminated only when a tool result contradicts it and confirmed only when a tool result supports it. "
    "4) Call exactly one tool at a time and only from the provided tools. "
    "5) Before a fix, state evidence, confidence, risk, rollback plan and verification checks. "
    "6) After any fix, call verify_recovery; do not say recovered unless it passes, then call resolve_incident. "
    "7) If no safe approved tool fits, confidence is below 0.6, risk is high, or verification fails, call page_human with your evidence. "
    "8) Be concise."
)


def _convert_schema_to_genai_types():
    """Convert TOOL_DECLARATIONS dictionary to google.genai types."""
    try:
        from google.genai import types
        decls = []
        for d in TOOL_DECLARATIONS:
            decls.append(types.FunctionDeclaration(
                name=d["name"],
                description=d["description"],
                parameters=d.get("parameters"),
            ))
        return decls
    except Exception:
        return []


def run_agent(
    S: Dict[str, Any],
    client: Optional[Any] = None,
    on_step: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    """Execute the incident response loop.

    Switches gracefully to fallback if client is None, call limit is reached,
    or API errors occur.
    """
    def step_cb():
        if on_step:
            on_step(S)

    # If already running in fallback mode or client not provided
    if S.get("mode") == "fallback" or client is None:
        if not S.get("mode_reason"):
            S["mode_reason"] = "API key not configured"
        S["mode"] = "fallback"
        return run_fallback_step(S, on_step=on_step)

    # Initialize Gemini message history if starting fresh
    if not S.get("contents"):
        incident = S.get("incident") or {}
        sig = incident.get("signature") or build_signature(S)

        # Pre-check memory for runbook guidance
        memory_match = find_similar_incident(S, sig)
        user_msg = (
            f"Active incident detected: {incident.get('id', 'INC-UNKNOWN')}\n"
            f"Alert: {incident.get('alert', 'Unspecified')}\n"
            f"Severity: {incident.get('severity', 'CRITICAL')}\n"
        )
        if memory_match:
            user_msg += (
                f"\n[INCIDENT MEMORY MATCH]: Similar prior incident {memory_match.get('id')} found.\n"
                f"Historical runbook: {memory_match.get('runbook')}\n"
                f"Requirement: Run at least ONE confirmation check before applying any fix."
            )
        else:
            user_msg += "\nInvestigate root cause using read tools, maintain 2-3 competing hypotheses, and remediate safely."

        from google.genai import types
        S["contents"] = [
            types.Content(role="user", parts=[types.Part.from_text(text=user_msg)])
        ]

    from google.genai import types
    genai_decls = _convert_schema_to_genai_types()
    gen_config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=[types.Tool(function_declarations=genai_decls)] if genai_decls else None,
        temperature=0.2,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        tool_config=types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(mode="ANY")
        ),
        http_options=types.HttpOptions(timeout=20.0),
    )

    turn = 0
    retry_count = 0

    while turn < MAX_TURNS:
        turn += 1

        # Check call limit constraint (CALL_LIMIT = 30)
        if S.get("llm_calls", 0) >= CALL_LIMIT:
            S["mode"] = "fallback"
            S["mode_reason"] = f"LLM call limit reached ({CALL_LIMIT} calls)"
            return run_fallback_step(S, on_step=on_step)

        # Call Gemini model
        try:
            S["llm_calls"] = S.get("llm_calls", 0) + 1
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=S["contents"],
                config=gen_config,
            )
            retry_count = 0
        except Exception as e:
            err_msg = str(e)
            if retry_count == 0:
                retry_count += 1
                time.sleep(1.0)
                continue
            # Second failure: switch to fallback policy
            S["mode"] = "fallback"
            S["mode_reason"] = f"API error: {err_msg[:60]}"
            return run_fallback_step(S, on_step=on_step)

        # Append model response to contents unchanged (preserves thought signatures)
        candidate = response.candidates[0] if response.candidates else None
        if not candidate or not candidate.content:
            if retry_count == 0:
                retry_count += 1
                continue
            S["mode"] = "fallback"
            S["mode_reason"] = "Model returned empty candidate"
            return run_fallback_step(S, on_step=on_step)

        S["contents"].append(candidate.content)

        # Extract function calls from candidate parts
        function_calls = []
        for part in candidate.content.parts:
            if hasattr(part, "function_call") and part.function_call:
                function_calls.append(part.function_call)

        if not function_calls:
            # Model generated only text; prompt it to use tools
            S["contents"].append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text="Please call an appropriate tool to proceed with the investigation.")],
                )
            )
            continue

        # Rule: Execute FIRST function call only; skip extras
        first_call = function_calls[0]
        tool_name = first_call.name
        tool_args = dict(first_call.args) if first_call.args else {}

        # Diagnostic call budget check (at 5 calls tell the model to decide)
        if is_diagnostic_tool(tool_name) and S.get("diag_calls", 0) >= 4:
            tool_res = execute_tool(S, tool_name, tool_args)
            tool_res["budget_warning"] = "Diagnostic budget reached (5 calls): You must now decide on an action (apply fix or page_human)."
        else:
            tool_res = execute_tool(S, tool_name, tool_args)

        step_cb()

        # Build responses for all calls in this turn (first get real result, extras get skipped)
        response_parts = [
            types.Part.from_function_response(
                name=tool_name,
                response={"result": tool_res},
            )
        ]
        for extra in function_calls[1:]:
            response_parts.append(
                types.Part.from_function_response(
                    name=extra.name,
                    response={"result": {"status": "skipped", "message": "one tool at a time"}},
                )
            )

        S["contents"].append(types.Content(role="user", parts=response_parts))

        # Check terminal and paused states
        if tool_res.get("status") == "approval_required":
            S["phase"] = "AWAITING_APPROVAL"
            return {"status": "awaiting_approval", "pending": S.get("pending")}

        if S.get("phase") in ("RESOLVED", "ESCALATED"):
            return {"status": S["phase"].lower()}

    return {"status": "max_turns_exceeded"}


def resume_after_approval(
    S: Dict[str, Any],
    client: Optional[Any],
    approved: bool,
    on_step: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    """Resume agent execution following human approval decision."""
    pending = S.get("pending")
    if not pending:
        return {"status": "no_pending_action"}

    tool_name = pending.get("tool", "rollback_config")
    tool_args = pending.get("args", {})

    if approved:
        # Execute tool with approved=True
        res = execute_tool(S, tool_name, tool_args, approved=True)
        S["pending"] = None
        S["phase"] = "REMEDIATING"
        if on_step:
            on_step(S)

        # If Gemini client is active, append human approval response to contents
        if S.get("mode") == "gemini" and client is not None:
            from google.genai import types
            S["contents"].append(
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_function_response(
                            name=tool_name,
                            response={
                                "result": res,
                                "human_approval": "APPROVED by human supervisor. Proceed to verify recovery.",
                            },
                        )
                    ],
                )
            )
            return run_agent(S, client, on_step=on_step)
        else:
            # Fallback path after approval
            return run_fallback_step(S, on_step=on_step)
    else:
        # Human rejected the proposal
        S["pending"] = None
        rejection_res = {
            "status": "rejected_by_human",
            "message": "Human supervisor rejected proposed action. Page human on-call with current evidence packet.",
        }
        if S.get("mode") == "gemini" and client is not None:
            from google.genai import types
            S["contents"].append(
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_function_response(
                            name=tool_name,
                            response={"result": rejection_res},
                        )
                    ],
                )
            )
            return run_agent(S, client, on_step=on_step)
        else:
            # Fallback policy when rejected: page human
            execute_tool(
                S,
                "page_human",
                {
                    "summary": "Human operator rejected automated rollback.",
                    "evidence": "Operator declined approval for configuration rollback.",
                    "recommended_next_step": "Investigate deployment manually with engineering team.",
                },
            )
            if on_step:
                on_step(S)
            return {"status": "escalated"}
