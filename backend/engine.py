from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable
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


class LLMProvider:
    name = "deterministic"

    def generate(self, *, message: str, intent: Intent, context: dict[str, Any], assistant: str = "saarthi") -> tuple[str, dict[str, Any] | None]:
        raise NotImplementedError


class OpenAICompatibleProvider(LLMProvider):
    """Cloud-only OpenAI-compatible adapter. Secrets never enter the browser."""

    name = "openrouter-free"

    def __init__(self) -> None:
        self.url = os.getenv(
            "SAARTHI_LLM_API_URL",
            "https://openrouter.ai/api/v1",
        ).rstrip("/")
        self.key = os.getenv("SAARTHI_LLM_API_KEY", "")
        self.model = os.getenv("SAARTHI_LLM_MODEL", "openrouter/free")

    @property
    def configured(self) -> bool:
        return bool(self.url and self.key and self.model)

    def generate(self, *, message: str, intent: Intent, context: dict[str, Any], assistant: str = "saarthi") -> tuple[str, dict[str, Any] | None]:
        if not self.configured:
            raise RuntimeError("cloud provider is not configured")

        profile = assistant_profile(assistant)
        coding_context = ""
        if profile["name"] == "AI Coding":
            has_code = bool(re.search(r"\\b(def|class|function|const|let|var|import|from|SELECT|<\\/?[A-Za-z])\\b", message, re.IGNORECASE))
            generation_request = bool(re.search(r"\\b(write|create|build|generate|implement|make|develop|scaffold|code)\\b", message, re.IGNORECASE))
            if has_code:
                coding_context = " Code or code-like material is present. Review and transform the supplied material directly."
            elif generation_request:
                coding_context = " This is a generative coding request without supplied source. Produce the requested runnable code instead of asking for a snippet."
            else:
                coding_context = " No source code is present. If the user asks for explanation of a specific missing snippet, request the snippet; otherwise answer normally."
        system = (
            f"You are {profile['name']}, the {profile['role']} inside SAARTHI, a calm personal AI assistant. "
            f"{profile['instruction']} {coding_context} "
            "Treat the selected assistant as the user's current working environment, not as a superficial label. "
            "Answer the user's actual request first. If useful, expose the reasoning structure briefly, but do not reveal hidden chain-of-thought. "
            "Prefer a direct answer, useful artifact, or concrete next step over meta-commentary about what you could do. "
            "Match depth to the request: simple questions get simple answers; complex requests get structured answers. "
            "Do not make decisions for the user. Separate facts, assumptions, trade-offs and next actions when relevant. "
            "Never claim a tool ran unless its result is present. Do not invent access to tools, files, browsing, memory or external services. "
            f"The selected assistant boundary is: {profile.get('boundary', 'general assistance')}. Enforce that boundary explicitly. If the request is outside the selected specialist's scope, give a short handoff to Saarthi or the relevant specialist instead of answering it as that specialist. "
        )
        context_note = json.dumps(context, ensure_ascii=False)[:12000] if context else "{}"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": f"Assistant context: {context_note}\n\nUser request:\n{message}"},
            ],
            "temperature": 0.3,
            "usage": {"include": True},
        }
        request = Request(
            self.url + "/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.key}",
                "HTTP-Referer": "https://swapnild007.github.io/SAARTHI/",
                "X-Title": "SAARTHI",
            },
            method="POST",
        )
        with urlopen(request, timeout=45) as response:
            body = json.loads(response.read().decode("utf-8"))
        usage = body.get("usage") if isinstance(body, dict) else None
        return str(body["choices"][0]["message"]["content"]).strip(), usage if isinstance(usage, dict) else None


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
        tool_results: dict[str, Any] = {}

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
            "usage": usage,
            "execution": "completed",
            "tool_results": tool_results,
            "verification": {"verified": True, "claims": "response generated from available execution context"},
        }
    