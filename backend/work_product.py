from __future__ import annotations

from typing import Any

from .verification import verify_run


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
    """Build a stable delivery contract without overstating verification."""
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

    provider = str(verification.get("provider") or "")
    execution = str(verification.get("execution") or "completed")
    verification_out = verify_run(
        objective=objective,
        reply=reply,
        tool_results=tool_results,
        execution=execution,
        provider=provider,
    )
    if verification.get("claims"):
        verification_out["runtime_claim"] = str(verification["claims"])[:500]

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
