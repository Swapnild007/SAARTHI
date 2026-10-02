from __future__ import annotations

from typing import Any


_ARTIFACT_BY_INTENT = {
    "research": "research_brief",
    "search": "research_brief",
    "analyze": "analysis_brief",
    "calculate": "calculation",
    "convert": "conversion",
    "plan": "execution_plan",
    "task": "execution_plan",
    "workflow": "workflow",
    "briefing": "briefing",
}


def _as_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def infer_deliverable_type(intent: str, orchestration: dict[str, Any] | None = None) -> str:
    orchestration = orchestration or {}
    artifacts = _as_list(orchestration.get("artifacts"))
    intent_name = str(intent or "").lower()
    for artifact in artifacts:
        if artifact:
            # Prefer an industry artifact when it is clearly aligned with the request.
            if intent_name in {"research", "search"} and "research" in artifact:
                return artifact
            if intent_name == "analyze" and ("analysis" in artifact or "review" in artifact):
                return artifact
            if intent_name == "plan" and ("plan" in artifact or "roadmap" in artifact):
                return artifact
    return _ARTIFACT_BY_INTENT.get(intent_name, "decision_brief")


def build_work_product(
    *,
    objective: str,
    intent: str,
    reply: str,
    orchestration: dict[str, Any] | None = None,
    tool_results: dict[str, Any] | None = None,
    verification: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a stable, machine-readable delivery contract around every run.

    This does not pretend the model's prose is factually verified. Verification
    describes what SAARTHI actually checked or executed in the runtime.
    """
    orchestration = orchestration or {}
    tool_results = tool_results or {}
    verification = verification or {}

    actions: list[str] = []
    if orchestration.get("internal_specialist"):
        actions.append(f"Internally routed to {orchestration['active_capability']}.")
    if orchestration.get("industry") and orchestration.get("industry") != "General":
        actions.append(f"Applied {orchestration['industry']} industry context.")
    if orchestration.get("workflow"):
        actions.append("Applied the configured industry workflow/capability mapping.")
    if tool_results:
        actions.append(f"Executed {len(tool_results)} server-side execution step(s).")
    if not actions:
        actions.append("Reasoned over the supplied objective and available conversation context.")

    evidence: list[dict[str, Any]] = []
    for name, result in tool_results.items():
        if isinstance(result, dict):
            evidence.append({
                "source": name,
                "type": "runtime_result",
                "available": True,
                "summary": (
                    result.get("claims")
                    or result.get("state")
                    or result.get("service")
                    or f"{name} completed"
                ),
            })
        else:
            evidence.append({"source": name, "type": "runtime_result", "available": True})

    verification_out = {
        "status": "runtime_verified",
        "scope": (
            "Confirms the SAARTHI runtime path and listed tool executions; "
            "it does not independently fact-check model-generated prose."
        ),
        "tool_count": len(tool_results),
        "claims": verification.get("claims"),
    }

    return {
        "version": "1.0",
        "objective": str(objective or "").strip(),
        "industry": orchestration.get("industry") or "General",
        "capability": orchestration.get("active_capability") or "Saarthi",
        "deliverable_type": infer_deliverable_type(intent, orchestration),
        "journey": orchestration.get("industry_coverage", {}).get("journey"),
        "coverage": _as_list(orchestration.get("industry_coverage", {}).get("coverage")),
        "artifact_bundle": _as_list(orchestration.get("industry_coverage", {}).get("artifact_bundle")),
        "assumptions": [],
        "actions_taken": actions,
        "evidence": evidence,
        "deliverable": str(reply or "").strip(),
        "verification": verification_out,
        "next_actions": [],
    }
