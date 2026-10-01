from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal
from urllib.request import Request as UrlRequest, urlopen

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .engine import SaarthiEngine
from .agent_capabilities import AGENT_CAPABILITIES, INDUSTRY_PACKS

app = FastAPI(title="SAARTHI Cloud API", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("SAARTHI_ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Serve the premium static SAARTHI frontend from the same FastAPI application.
# Keeping frontend and API in one ASGI app avoids Vercel routing ambiguity.
for _path_name in ("assets", "scripts", "styles", "config"):
    _path = PROJECT_ROOT / _path_name
    if _path.is_dir():
        app.mount(f"/{_path_name}", StaticFiles(directory=str(_path)), name=_path_name)


@app.get("/", include_in_schema=False)
def frontend():
    return FileResponse(PROJECT_ROOT / "index.html")

Mode = Literal[
    "chat", "help", "research", "search", "analyze", "plan", "remember",
    "recall", "tasks", "task", "remind", "workflow", "workflows",
    "briefing", "system", "settings", "voice",
]


Assistant = Literal["saarthi", "coding", "research", "create", "data_analyst", "analyze", "plan"]


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
        "ai_gateway_routes": len(engine.cloud.routes),
        "ai_gateway_active_route": engine.cloud.last_route if engine.cloud.configured else None,
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


@app.get("/api/capabilities")
def capabilities():
    return {
        "ok": True,
        "agents": AGENT_CAPABILITIES,
        "industries": INDUSTRY_PACKS,
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
            now = datetime.now(timezone.utc)
            start = now - timedelta(days=30)
            headers = {
                "Authorization": f"Bearer {management_key}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
            meta_request = UrlRequest(
                base_url + "/analytics/meta",
                headers={k: v for k, v in headers.items() if k != "Content-Type"},
                method="GET",
            )
            with urlopen(meta_request, timeout=15) as response:
                meta = json.loads(response.read().decode("utf-8"))
            result["analytics_meta"] = meta

            def analytics_query(dimensions: list[str] | None = None) -> dict[str, Any]:
                payload = {
                    "metrics": ["total_usage", "request_count", "tokens_total"],
                    "dimensions": dimensions or [],
                    "time_range": {"start": start.isoformat(), "end": now.isoformat()},
                    "limit": 20,
                    "order_by": {"field": "total_usage", "direction": "desc"},
                }
                req = UrlRequest(
                    base_url + "/analytics/query",
                    data=json.dumps(payload).encode("utf-8"),
                    headers=headers,
                    method="POST",
                )
                with urlopen(req, timeout=20) as response:
                    return json.loads(response.read().decode("utf-8"))

            result["analytics_30d"] = analytics_query()
            result["analytics_by_model_30d"] = analytics_query(["model"])
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
