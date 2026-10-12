"""Deterministic verification primitives for SAARTHI run results.

This module distinguishes runtime checks from factual verification. Successful
model generation alone is never treated as proof that generated claims are true.
"""
from __future__ import annotations

from typing import Any


def verify_run(
    *,
    objective: str,
    reply: str,
    tool_results: dict[str, Any] | None = None,
    execution: str = "completed",
    provider: str | None = None,
) -> dict[str, Any]:
    """Return an auditable, conservative verification summary for a run."""
    objective_text = str(objective or "").strip()
    reply_text = str(reply or "").strip()
    tools = tool_results if isinstance(tool_results, dict) else {}
    checks: list[dict[str, Any]] = [
        {
            "name": "objective_present",
            "status": "passed" if objective_text else "failed",
            "detail": "A non-empty objective was supplied." if objective_text else "No objective was supplied.",
        },
        {
            "name": "response_present",
            "status": "passed" if reply_text else "failed",
            "detail": "A non-empty response was produced." if reply_text else "No response was produced.",
        },
        {
            "name": "execution_completed",
            "status": "passed" if execution == "completed" else "blocked",
            "detail": f"Execution state: {execution or 'unknown'}.",
        },
        {
            "name": "tool_results_available",
            "status": "passed" if tools else "not_applicable",
            "detail": f"{len(tools)} execution result(s) are available." if tools else "No deterministic tool result was attached to this run.",
        },
    ]
    deterministic = bool(tools) and (
        str(provider or "").startswith("system.")
        or all(str(name).startswith("system.") for name in tools)
    )
    if deterministic:
        factual_scope = "Deterministic server-side tool output is available; only the recorded tool result is verified."
        status = "partially_verified"
    else:
        factual_scope = "The response was produced, but model-generated claims have not been independently fact-checked."
        status = "runtime_checked"
    if any(item["status"] == "failed" for item in checks):
        status = "failed"
    elif execution != "completed":
        status = "incomplete"
    return {
        "status": status,
        "verified": status in {"partially_verified", "runtime_checked"},
        "scope": factual_scope,
        "checks": checks,
        "tool_count": len(tools),
        "provider": str(provider or "unknown"),
        "limitations": [
            "No independent factual verification of model-generated prose was performed."
        ] if not deterministic else [
            "Verification applies to the recorded deterministic tool result, not every sentence in the response."
        ],
    }
