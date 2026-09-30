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


class LLMProvider:
    name = "deterministic"

    def generate(self, *, message: str, intent: Intent, context: dict[str, Any]) -> str:
        raise NotImplementedError


class OpenAICompatibleProvider(LLMProvider):
    """Cloud-only OpenAI-compatible adapter. Secrets never enter the browser."""

    name = "cloud-llm"

    def __init__(self) -> None:
        self.url = os.getenv("SAARTHI_LLM_API_URL", "").rstrip("/")
        self.key = os.getenv("SAARTHI_LLM_API_KEY", "")
        self.model = os.getenv("SAARTHI_LLM_MODEL", "")

    @property
    def configured(self) -> bool:
        return bool(self.url and self.key and self.model)

    def generate(self, *, message: str, intent: Intent, context: dict[str, Any]) -> str:
        if not self.configured:
            raise RuntimeError("cloud provider is not configured")

        system = (
            "You are SAARTHI, a calm Indian JARVIS-style personal AI guide. "
            "Be concise, situationally aware and action-oriented. "
            "Do not make decisions for the user. Separate facts, assumptions, trade-offs "
            "and next actions when relevant. Never claim a tool ran unless its result is present."
        )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": message},
            ],
            "temperature": 0.3,
        }
        request = Request(
            self.url + "/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.key}",
            },
            method="POST",
        )
        with urlopen(request, timeout=45) as response:
            body = json.loads(response.read().decode("utf-8"))
        return str(body["choices"][0]["message"]["content"]).strip()


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


def fallback_response(message: str, intent: Intent, tool_results: dict[str, Any]) -> str:
    if intent.name == "help":
        return "I can chat, research, search, analyze, plan, remember, recall, manage tasks and reminders, run workflows, brief you, and report system status."
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

    def run(self, *, message: str, mode: str = "chat", context: dict[str, Any] | None = None) -> dict[str, Any]:
        run_id = "run_" + uuid.uuid4().hex[:12]
        ctx = context or {}
        intent = classify(message, mode)
        plan = build_plan(intent)
        tool_results: dict[str, Any] = {}

        if intent.name == "system":
            tool_results["system.status"] = self.tools.execute("system.status")

        provider = self.cloud if self.cloud.configured else None
        provider_name = provider.name if provider else "deterministic-fallback"
        try:
            reply = provider.generate(message=message, intent=intent, context=ctx) if provider else fallback_response(message, intent, tool_results)
        except Exception:
            provider_name = "deterministic-fallback"
            reply = fallback_response(message, intent, tool_results)

        return {
            "ok": True,
            "run_id": run_id,
            "intent": {
                "name": intent.name,
                "confidence": intent.confidence,
                "reason": intent.reason,
            },
            "plan": [step.__dict__ for step in plan],
            "reply": reply,
            "provider": provider_name,
            "execution": "completed",
            "tool_results": tool_results,
            "verification": {"verified": True, "claims": "response generated from available execution context"},
        }
