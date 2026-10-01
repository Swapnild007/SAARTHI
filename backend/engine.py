from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from .attachments import inspect_attachments, provider_content_parts
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class Intent:
    name: str
    confidence: float
    reason: str


@dataclass(frozen=True)
class PlanStep:
    id: str
    label: str
    status: str = "ready"


class ToolRegistry:
    """Small, explicit tool boundary. Add tools here; never execute arbitrary code."""

    def __init__(self) -> None:
        self._tools: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
            "system.time": self._time,
            "system.status": self._status,
        }

    def names(self) -> list[str]:
        return sorted(self._tools)

    def execute(self, name: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
        tool = self._tools.get(name)
        if not tool:
            raise ValueError(f"Tool not registered: {name}")
        return tool(args or {})

    @staticmethod
    def _time(_: dict[str, Any]) -> dict[str, Any]:
        return {"utc": datetime.now(timezone.utc).isoformat()}

    @staticmethod
    def _status(_: dict[str, Any]) -> dict[str, Any]:
        return {"service": "saarthi-engine", "state": "ready"}


ASSISTANT_PROFILES: dict[str, dict[str, str]] = {
    "saarthi": {
        "name": "Saarthi",
        "role": "personal AI assistant",
        "instruction": (
            "Be the user's primary personal assistant and general thinking partner. This is the broadest environment. "
            "Handle everyday questions, voice-assistant style requests, personal organization, learning, planning, decisions, writing, problem-solving and practical tasks. "
            "Use the current Saarthi conversation as the only conversational working memory for this turn. Do not assume context from another assistant or another thread. "
            "For decisions, separate facts, assumptions, constraints, trade-offs and options and leave decision authority with the user. "
            "For planning, convert outcomes into ordered actions, dependencies and checkpoints. For problems, diagnose before prescribing. "
            "When a specialist task clearly belongs to Coding, Research, Create, Analyze or Plan, explain briefly that the specialist environment is designed for that task and ask the user whether they want to switch; do not silently impersonate the specialist. "
            "This environment may still answer ordinary coding, research, writing, analysis or planning questions when they are part of a broader personal-assistant request, because Saarthi is the general assistant. "
            "Stay calm, practical and conversational. Never fabricate facts, citations, access, memory, tool results or completed actions."
        ),
        "boundary": "general personal assistance; broad requests are allowed, with specialist handoff for clearly specialized work",
    },
    "coding": {
        "name": "AI Coding",
        "role": "software engineering assistant",
        "instruction": (
            "Act only as a software engineering specialist. Design, implement, debug, refactor, test, review and explain software. "
            "Treat the Coding conversation as a separate workspace. Never use or reveal messages, memories or conclusions from Saarthi or another assistant. "
            "If the user asks a general personal, life, shopping, casual, relationship or other non-software question, do not answer it as Coding. "
            "Briefly state that AI Coding is restricted to software work and direct the user to Saarthi for general assistance. "
            "For coding requests, work directly from supplied code, errors, repository context or requirements. If source code is not supplied and the task is clearly to build something, produce a complete runnable solution instead of asking for a snippet. "
            "Prefer production-ready code, explicit file boundaries, tests and concrete debugging steps. Never claim to have inspected a repository, file, build or test unless that evidence is present."
        ),
        "boundary": "software engineering only",
    },
    "research": {
        "name": "Research",
        "role": "research and evidence synthesis assistant",
        "instruction": (
            "Act only as a research specialist. Investigate questions, gather and compare evidence, explain source quality, identify uncertainty and synthesize findings. "
            "Treat the Research conversation as a separate workspace. Never use or reveal messages, memories or conclusions from another assistant. "
            "If the user asks for coding, personal assistance, creative drafting, data analysis or execution planning rather than research, do not answer that task as Research. "
            "Briefly state the scope boundary and direct the user to the appropriate specialist or Saarthi. Never invent sources or citations."
        ),
        "boundary": "research, evidence and synthesis only",
    },
    "create": {
        "name": "Create",
        "role": "creative and writing assistant",
        "instruction": (
            "Act only as a creative production specialist. Create, draft, rewrite, edit, brainstorm and shape writing, concepts, prompts and creative assets. "
            "Treat the Create conversation as a separate workspace. Never use or reveal messages, memories or conclusions from another assistant. "
            "If the user asks for coding, research, data analysis, personal assistance or detailed execution planning rather than a creative output, do not answer that task as Create. "
            "Briefly state the scope boundary and direct the user to the appropriate specialist or Saarthi. Match the requested format, audience and tone."
        ),
        "boundary": "creative production and writing only",
    },
    "data_analyst": {
        "name": "Data Analyst",
        "role": "quantitative data analysis and visualization specialist",
        "instruction": (
            "Act only as a quantitative data analysis specialist. Work with spreadsheets, CSV/JSON datasets, metrics, statistics, trends, anomalies, forecasting, SQL/Python reasoning and dashboards. "
            "Treat the Data Analyst conversation as a separate workspace. Never use or reveal messages, memories or conclusions from another assistant. "
            "When data is attached, use the supplied data rather than inventing values. State data quality issues, assumptions and limitations. "
            "When a chart materially improves the answer or the user asks for one, produce a chart specification using a <saarthi-chart>{JSON}</saarthi-chart> block. The JSON must contain chartType (bar, line, pie or scatter), title, xKey, series and data. Every plotted value must come from supplied data or an explicitly labeled calculation. "
            "When the user asks for a process, relationship or flow diagram rather than a quantitative chart, produce a <saarthi-diagram>{JSON}</saarthi-diagram> block with title, nodes and edges. "
            "Do not fabricate measurements. Do not answer unrelated creative writing, general personal assistance or software implementation requests as Data Analyst."
        ),
        "boundary": "quantitative data, statistics, datasets and visualization only",
    },
    "analyze": {
        "name": "Analyze",
        "role": "data, document and visual analysis assistant",
        "instruction": (
            "Act only as an analysis specialist. Analyze data, documents, images, systems and situations by separating evidence, patterns, assumptions, risks, trade-offs and conclusions. "
            "Treat the Analyze conversation as a separate workspace. Never use or reveal messages, memories or conclusions from another assistant. "
            "If the user asks for general personal assistance, creative writing, software implementation, source research or a step-by-step execution plan rather than analysis, do not answer that task as Analyze. "
            "Briefly state the scope boundary and direct the user to the appropriate specialist or Saarthi. Do not invent missing data."
        ),
        "boundary": "analysis of data, documents, visuals and situations only",
    },
    "plan": {
        "name": "Plan",
        "role": "planning and execution strategy assistant",
        "instruction": (
            "Act only as a planning specialist. Turn goals into ordered actions, dependencies, constraints, checkpoints, contingencies and next steps. "
            "Treat the Plan conversation as a separate workspace. Never use or reveal messages, memories or conclusions from another assistant. "
            "If the user asks for general conversation, coding implementation, research evidence, creative drafting or analytical interpretation rather than planning, do not answer that task as Plan. "
            "Briefly state the scope boundary and direct the user to the appropriate specialist or Saarthi. Do not silently make decisions on the user's behalf."
        ),
        "boundary": "planning and execution strategy only",
    },
}

def assistant_profile(assistant: str | None) -> dict[str, str]:
    return ASSISTANT_PROFILES.get(str(assistant or "").lower(), ASSISTANT_PROFILES["saarthi"])

def specialist_boundary_response(assistant: str, message: str) -> str | None:
    """Deterministic scope guard for specialist agents before any model call."""
    text = message.strip().lower()
    if assistant == "saarthi":
        return None

    outside_patterns = {
        "coding": r"\b(weather|recipe|restaurant|dating|relationship|movie|travel|personal advice|what should i eat)\b",
        "research": r"\b(write code|debug|fix this code|implement|refactor|deploy|build this app)\b",
        "create": r"\b(debug|implement|refactor|sql query|python script|analyze this dataset|calculate|research this)\b",
        "analyze": r"\b(write a|draft an email|write an email|write a story|write a poem|code this|implement)\b",
        "data_analyst": r"\b(write a story|write a poem|draft an email|relationship advice|casual chat)\b",
        "plan": r"\b(debug|write code|implement|research and cite|write a poem|casual chat|what is the weather)\b",
    }
    pattern = outside_patterns.get(assistant)
    if pattern and re.search(pattern, text, re.IGNORECASE):
        target = {
            "coding": "Saarthi", "research": "Research", "create": "Create",
            "analyze": "Analyze", "data_analyst": "Data Analyst", "plan": "Plan"
        }.get(assistant, "Saarthi")
        if assistant == "coding":
            target = "Saarthi"
        return f"{ASSISTANT_PROFILES[assistant]['name']} is restricted to {ASSISTANT_PROFILES[assistant]['boundary']}. Please use {target} for this request."
    return None




class LLMProvider:
    name = "deterministic"

    def generate(self, *, message: str, intent: Intent, context: dict[str, Any], assistant: str = "saarthi") -> tuple[str, dict[str, Any] | None]:
        raise NotImplementedError


class OpenAICompatibleProvider(LLMProvider):
    """OpenAI-compatible gateway with ordered routes and automatic failover.

    Configure SAARTHI_LLM_ROUTES_JSON as a JSON array of:
    {"name":"primary","url":"https://.../v1","key":"...","model":"..."}.
    If unset, the legacy SAARTHI_LLM_API_URL/KEY/MODEL variables remain supported.
    """
    name = "ai-gateway"

    def __init__(self) -> None:
        raw = os.getenv("SAARTHI_LLM_ROUTES_JSON", "").strip()
        routes: list[dict[str, str]] = []
        if raw:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    routes = [r for r in parsed if isinstance(r, dict) and r.get("key") and r.get("url") and r.get("model")]
            except json.JSONDecodeError:
                routes = []
        if not routes:
            routes = [{
                "name": os.getenv("SAARTHI_LLM_PROVIDER_NAME", "OpenRouter"),
                "url": os.getenv("SAARTHI_LLM_API_URL", "https://openrouter.ai/api/v1"),
                "key": os.getenv("SAARTHI_LLM_API_KEY", ""),
                "model": os.getenv("SAARTHI_LLM_MODEL", "openrouter/free"),
            }]
        self.routes = routes
        self.last_route = routes[0].get("name", "unknown") if routes else "unavailable"
        self.last_failures: list[dict[str, str]] = []

    @property
    def configured(self) -> bool:
        return bool(self.routes and any(r.get("url") and r.get("key") and r.get("model") for r in self.routes))

    def _request(self, route: dict[str, str], *, message: str, system: str, context: dict[str, Any], assistant: str) -> tuple[str, dict[str, Any] | None]:
        inspected = inspect_attachments(context.get("attachments") if isinstance(context, dict) else [])
        _, content_parts = provider_content_parts(message, inspected)
        payload = {
            "model": route["model"],
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": content_parts if len(content_parts) > 1 else content_parts[0]["text"]},
            ],
            "temperature": 0.3,
            "usage": {"include": True},
        }
        request = Request(
            route["url"].rstrip("/") + "/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {route['key']}",
                "HTTP-Referer": "https://swapnild007.github.io/SAARTHI/",
                "X-Title": "SAARTHI",
            },
            method="POST",
        )
        with urlopen(request, timeout=45) as response:
            body = json.loads(response.read().decode("utf-8"))
        usage = body.get("usage") if isinstance(body, dict) else None
        reply = str(body["choices"][0]["message"]["content"]).strip()
        self.last_route = route.get("name", route.get("model", "unknown"))
        return reply, usage if isinstance(usage, dict) else None

    def generate(self, *, message: str, intent: Intent, context: dict[str, Any], assistant: str = "saarthi") -> tuple[str, dict[str, Any] | None]:
        if not self.configured:
            raise RuntimeError("no AI gateway route is configured")
        profile = assistant_profile(assistant)
        coding_context = ""
        if profile["name"] == "AI Coding":
            has_code = bool(re.search(r"\b(def|class|function|const|let|var|import|from|SELECT|<\\/?[A-Za-z])\b", message, re.IGNORECASE))
            generation_request = bool(re.search(r"\b(write|create|build|generate|implement|make|develop|scaffold|code)\b", message, re.IGNORECASE))
            coding_context = (
                " Code or code-like material is present. Review and transform the supplied material directly."
                if has_code else
                " This is a generative coding request without supplied source. Produce the requested runnable code."
                if generation_request else
                " No source code is present. Answer normally unless a missing snippet is essential."
            )
        attachment_hint = ""
        if context.get("attachments"):
            attachment_hint = (
                " Attachments are available in the request context. Use their extracted contents and images. "
                "For Data Analyst, never invent values that are not in the supplied dataset."
            )
        chart_hint = ""
        if assistant == "data_analyst":
            chart_hint = (
                " For charts use <saarthi-chart>{JSON}</saarthi-chart>. For diagrams use <saarthi-diagram>{JSON}</saarthi-diagram>. "
                "Keep JSON valid and concise. Do not put prose inside these blocks."
            )
        system = (
            f"You are {profile['name']}, the {profile['role']} inside SAARTHI, a calm personal AI assistant. "
            f"{profile['instruction']} {coding_context}{attachment_hint}{chart_hint} "
            "Treat the selected assistant as the user's current working environment, not as a superficial label. "
            "Answer the user's actual request first. Do not reveal hidden chain-of-thought. "
            "Never claim a tool ran unless its result is present. Do not invent access to tools, files, browsing, memory or external services. "
            f"The selected assistant boundary is: {profile.get('boundary', 'general assistance')}. Enforce that boundary explicitly."
        )
        failures: list[dict[str, str]] = []
        for route in self.routes:
            try:
                reply, usage = self._request(route, message=message, system=system, context=context, assistant=assistant)
                self.last_failures = failures
                return reply, usage
            except Exception as exc:
                failures.append({"route": route.get("name", route.get("model", "unknown")), "error": str(exc)[:240]})
        self.last_failures = failures
        raise RuntimeError("all configured AI gateway routes failed")


def classify(message: str, requested_mode: str = "chat") -> Intent:
    text = message.strip().lower()
    explicit = {
        "/research": ("research", 1.0, "explicit command"),
        "/search": ("search", 1.0, "explicit command"),
        "/analyze": ("analyze", 1.0, "explicit command"),
        "/remember": ("remember", 1.0, "explicit command"),
        "/recall": ("recall", 1.0, "explicit command"),
        "/tasks": ("task", 1.0, "explicit command"),
        "/remind": ("remind", 1.0, "explicit command"),
        "/workflows": ("workflow", 1.0, "explicit command"),
        "/briefing": ("briefing", 1.0, "explicit command"),
        "/system": ("system", 1.0, "explicit command"),
        "/settings": ("settings", 1.0, "explicit command"),
        "/voice": ("voice", 1.0, "explicit command"),
        "/help": ("help", 1.0, "explicit command"),
    }
    token = text.split(maxsplit=1)[0] if text else ""
    if token in explicit:
        name, confidence, reason = explicit[token]
        return Intent(name, confidence, reason)

    mode_aliases = {
        "tasks": "task",
        "workflows": "workflow",
    }
    requested_mode = mode_aliases.get(requested_mode, requested_mode)
    if requested_mode not in {"chat", ""}:
        return Intent(requested_mode, 0.95, "UI-selected mode")

    patterns = [
        ("research", r"\b(research|deep dive|investigate|sources?)\b"),
        ("search", r"\b(search|find|look up|lookup)\b"),
        ("analyze", r"\b(analy[sz]e|compare|break down|trade[- ]?offs?)\b"),
        ("plan", r"\b(plan|roadmap|steps?|schedule)\b"),
        ("remember", r"\b(remember|save this|store this)\b"),
        ("recall", r"\b(recall|what did i|remember when|previously)\b"),
        ("task", r"\b(task|todo|to-do)\b"),
        ("remind", r"\b(remind|reminder)\b"),
        ("workflow", r"\b(workflow|automate|automation)\b"),
        ("briefing", r"\b(briefing|brief me|what matters today)\b"),
        ("system", r"\b(system status|health check|diagnostics)\b"),
        ("help", r"\b(help|what can you do|commands)\b"),
    ]
    for name, pattern in patterns:
        if re.search(pattern, text):
            return Intent(name, 0.82, "semantic command routing")
    return Intent("chat", 0.74, "general conversation")


def build_plan(intent: Intent) -> list[PlanStep]:
    common = [
        PlanStep("understand", "Understand request"),
        PlanStep("context", "Load available context"),
    ]
    tail = {
        "research": [PlanStep("retrieve", "Collect sources"), PlanStep("synthesize", "Synthesize findings")],
        "search": [PlanStep("retrieve", "Search available sources")],
        "analyze": [PlanStep("reason", "Analyze facts and trade-offs")],
        "plan": [PlanStep("plan", "Build an actionable plan")],
        "remember": [PlanStep("memory", "Prepare memory update")],
        "recall": [PlanStep("memory", "Retrieve relevant memory")],
        "task": [PlanStep("task", "Prepare task action")],
        "remind": [PlanStep("schedule", "Prepare reminder")],
        "workflow": [PlanStep("workflow", "Prepare workflow")],
        "briefing": [PlanStep("briefing", "Assemble briefing")],
        "system": [PlanStep("diagnose", "Check engine status")],
        "settings": [PlanStep("settings", "Prepare settings action")],
        "voice": [PlanStep("voice", "Prepare voice pipeline")],
        "help": [PlanStep("catalog", "Load command capabilities")],
        "chat": [PlanStep("reason", "Reason over the request")],
    }
    return common + tail.get(intent.name, tail["chat"]) + [PlanStep("respond", "Form response")]


def fallback_response(message: str, intent: Intent, tool_results: dict[str, Any], assistant: str = "saarthi") -> str:
    profile = assistant_profile(assistant)
    if intent.name == "help":
        return (
            f"{profile['name']} is active. "
            "I can chat, research, search, analyze, plan, remember, recall, manage tasks and reminders, "
            "run workflows, brief you, and report system status."
        )
    if intent.name == "system":
        return "SAARTHI engine is online. The command router, plan builder and tool boundary are ready."
    if intent.name == "remember":
        return "I can prepare this as a memory item. Persistent cloud memory will activate when the memory provider is connected."
    if intent.name == "recall":
        return "I can recall from persistent cloud memory once the memory provider is connected."
    if intent.name in {"task", "remind", "workflow"}:
        return f"I understood this as a {intent.name} request. The action boundary is ready; execution requires the connected cloud tool."
    if intent.name == "briefing":
        return "Briefing mode is ready. Connect calendar, tasks, weather and news providers to assemble your live briefing."
    if intent.name == "search":
        return "Search mode is ready. Connect a web-search provider to retrieve live sources."
    if intent.name == "research":
        return "Research mode is ready. Connect web retrieval and I will collect, compare and synthesize sources."
    if intent.name == "analyze":
        return "Analysis mode is ready. Give me the facts, document or situation and I will separate facts, assumptions, trade-offs and actions."
    if intent.name == "plan":
        return "Planning mode is ready. Give me the outcome you want and I will turn it into ordered steps."
    return f"I've understood the request as a general conversation: “{message[:180]}”."


class SaarthiEngine:
    def __init__(self) -> None:
        self.tools = ToolRegistry()
        self.cloud = OpenAICompatibleProvider()

    def run(
        self,
        *,
        message: str,
        mode: str = "chat",
        assistant: str = "saarthi",
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        run_id = "run_" + uuid.uuid4().hex[:12]
        ctx = context or {}
        assistant_id = str(assistant or "saarthi").lower()
        if assistant_id not in ASSISTANT_PROFILES:
            assistant_id = "saarthi"
        intent = classify(message, mode)
        plan = build_plan(intent)
        if assistant_id == "data_analyst":
            plan = [PlanStep("profile", "Profile supplied data"), PlanStep("validate", "Validate data quality"), PlanStep("analyze", "Calculate and analyze"), PlanStep("visualize", "Create requested visualization"), PlanStep("respond", "Explain findings")]
        tool_results: dict[str, Any] = {}
        boundary_reply = specialist_boundary_response(assistant_id, message)
        if boundary_reply:
            return {
                "ok": True,
                "run_id": run_id,
                "assistant": {
                    "id": assistant_id,
                    "name": ASSISTANT_PROFILES[assistant_id]["name"],
                    "role": ASSISTANT_PROFILES[assistant_id]["role"],
                    "boundary": ASSISTANT_PROFILES[assistant_id].get("boundary", "general assistance"),
                },
                "intent": {"name": intent.name, "confidence": intent.confidence, "reason": intent.reason},
                "plan": [step.__dict__ for step in plan],
                "reply": boundary_reply,
                "provider": "boundary-guard",
                "usage": None,
                "execution": "blocked-by-scope",
                "tool_results": {},
                "verification": {"verified": True, "claims": "specialist scope boundary enforced before model execution"},
            }

        if intent.name == "system":
            tool_results["system.status"] = self.tools.execute("system.status")

        provider = self.cloud if self.cloud.configured else None
        provider_name = provider.name if provider else "deterministic-fallback"
        usage: dict[str, Any] | None = None
        try:
            if provider:
                reply, usage = provider.generate(
                    message=message,
                    intent=intent,
                    context=ctx,
                    assistant=assistant_id,
                )
            else:
                reply = fallback_response(message, intent, tool_results, assistant_id)
        except Exception:
            provider_name = "deterministic-fallback"
            reply = fallback_response(message, intent, tool_results, assistant_id)

        return {
            "ok": True,
            "run_id": run_id,
            "assistant": {
                "id": assistant_id,
                "name": ASSISTANT_PROFILES[assistant_id]["name"],
                "role": ASSISTANT_PROFILES[assistant_id]["role"],
                "boundary": ASSISTANT_PROFILES[assistant_id].get("boundary", "general assistance"),
            },
            "intent": {
                "name": intent.name,
                "confidence": intent.confidence,
                "reason": intent.reason,
            },
            "plan": [step.__dict__ for step in plan],
            "reply": reply,
            "provider": provider_name,
            "route": self.cloud.last_route if self.cloud.configured else None,
            "failover": self.cloud.last_failures if self.cloud.configured else [],
            "usage": usage,
            "execution": "completed",
            "tool_results": tool_results,
            "verification": {"verified": True, "claims": "response generated from available execution context"},
        }
    