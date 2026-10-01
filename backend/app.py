from __future__ import annotations

import json
import os
from typing import Any, Literal
from urllib.request import Request as UrlRequest, urlopen

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .engine import SaarthiEngine

app = FastAPI(title="SAARTHI Cloud API", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("SAARTHI_ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

Mode = Literal[
    "chat", "help", "research", "search", "analyze", "plan", "remember",
    "recall", "tasks", "task", "remind", "workflow", "workflows",
    "briefing", "system", "settings", "voice",
]


Assistant = Literal["saarthi", "coding", "research", "create", "analyze", "plan"]


class CommandRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12000)
    mode: Mode = "chat"
    assistant: Assistant = "saarthi"
    conversation_id: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12000)
    assistant: Assistant = "saarthi"
    conversation_id: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)


engine = SaarthiEngine()


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "service": "saarthi-api",
        "architecture": "cloud",
        "engine": "jarvis-runtime-v1",
        "provider_configured": engine.cloud.configured,
        "tools": engine.tools.names(),
    }


@app.get("/api/menus")
def menus():
    return {
        "command": ["chat", "voice", "tasks", "actions", "runs"],
        "home": ["briefing", "status", "context"],
        "insights": ["research", "search", "analyze", "web", "sources"],
        "journey": ["tasks", "reminders", "workflows", "progress"],
        "memory": ["remember", "recall", "knowledge", "preferences"],
        "settings": ["model", "voice", "privacy", "connections", "permissions"],
    }


@app.get("/api/usage")
def usage():
    """Return OpenRouter usage without exposing any credential to the browser.

    The regular inference key can read its own time-windowed key totals from
    /api/v1/key. Historical Activity/Analytics data is optional and requires a
    separate management key kept server-side in SAARTHI_OPENROUTER_MANAGEMENT_KEY.
    """
    provider = engine.cloud
    if not provider.configured:
        return {"ok": False, "source": "unavailable", "reason": "provider_not_configured"}

    base_url = provider.url.rstrip("/")
    key = provider.key
    result: dict[str, Any] = {
        "ok": True,
        "source": "openrouter-key",
        "provider": "OpenRouter",
        "analytics_configured": bool(os.getenv("SAARTHI_OPENROUTER_MANAGEMENT_KEY")),
    }

    try:
        request = UrlRequest(
            base_url + "/key",
            headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
            method="GET",
        )
        with urlopen(request, timeout=15) as response:
            result["key"] = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        result["key_error"] = str(exc)

    management_key = os.getenv("SAARTHI_OPENROUTER_MANAGEMENT_KEY", "")
    if management_key:
        try:
            meta_request = UrlRequest(
                base_url + "/analytics/meta",
                headers={"Authorization": f"Bearer {management_key}", "Accept": "application/json"},
                method="GET",
            )
            with urlopen(meta_request, timeout=15) as response:
                meta = json.loads(response.read().decode("utf-8"))
            result["analytics_meta"] = meta
        except Exception as exc:
            result["analytics_error"] = str(exc)

    return result


@app.post("/api/command")
def command(request: CommandRequest):
    result = engine.run(
        message=request.message,
        mode=request.mode,
        assistant=request.assistant,
        context=request.context,
    )
    result["conversation_id"] = request.conversation_id
    return result


@app.post("/api/chat")
def chat(request: ChatRequest):
    result = engine.run(
        message=request.message,
        mode="chat",
        assistant=request.assistant,
        context=request.context,
    )
    result["conversation_id"] = request.conversation_id
    return result
