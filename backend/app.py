from __future__ import annotations

import json
import os
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal
from urllib.request import Request as UrlRequest, urlopen

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .engine import SaarthiEngine
from .agent_capabilities import AGENT_CAPABILITIES, INDUSTRY_PACKS

_docs_enabled = os.getenv("SAARTHI_ENABLE_DOCS", "").lower() in {"1", "true", "yes"}
app = FastAPI(
    title="SAARTHI Cloud API",
    version="0.4.0",
    docs_url="/docs" if _docs_enabled else None,
    redoc_url="/redoc" if _docs_enabled else None,
    openapi_url="/openapi.json" if _docs_enabled else None,
)

_allowed_origins_raw = os.getenv("SAARTHI_ALLOWED_ORIGINS", "").strip()
ALLOWED_ORIGINS = (
    [origin.strip() for origin in _allowed_origins_raw.split(",") if origin.strip()]
    if _allowed_origins_raw
    else [
        "https://saarthi-nine-chi.vercel.app",
        "https://swapnild007.github.io",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Accept", "Content-Type"],
    max_age=600,
)

# Defense-in-depth controls. Production-grade distributed rate limiting should
# also be enforced at the edge/API gateway because serverless instances are ephemeral.
_RATE_LIMIT = max(1, int(os.getenv("SAARTHI_RATE_LIMIT_PER_MINUTE", "60")))
_rate_buckets: dict[str, deque[float]] = defaultdict(deque)


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    if request.url.path.startswith("/api/"):
        now = time.monotonic()
        forwarded = request.headers.get("x-forwarded-for", "")
        client_id = forwarded.split(",", 1)[0].strip() or (
            request.client.host if request.client else "unknown"
        )
        bucket = _rate_buckets[client_id]
        cutoff = now - 60.0
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if len(bucket) >= _RATE_LIMIT:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please retry shortly."},
                headers={"Retry-After": "60", "Cache-Control": "no-store"},
            )
        bucket.append(now)

    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Permissions-Policy",
        "camera=(), geolocation=(self), microphone=(self), payment=(), usb=()",
    )
    response.headers.setdefault("X-DNS-Prefetch-Control", "off")
    if request.url.scheme == "https":
        response.headers.setdefault(
            "Strict-Transport-Security",
            "max-age=31536000; includeSubDomains",
        )
    if request.url.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
    if request.url.path == "/":
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data: blob:; "
            "media-src 'self' blob:; "
            "connect-src 'self' https://saarthi-nine-chi.vercel.app https://swapnild007.github.io https://api.open-meteo.com https://api.bigdatacloud.net https://ipwho.is; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "frame-ancestors 'none'; "
            "form-action 'self'",
        )
    return response

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
    # Keep infrastructure details out of the public health contract.
    return {
        "ok": True,
        "service": "saarthi-api",
        "architecture": "cloud",
        "engine": "saarthi-runtime-v1",
        "provider_configured": engine.cloud.configured,
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


def _execute_command(request: CommandRequest) -> dict[str, Any]:
    result = engine.run(
        message=request.message,
        mode=request.mode,
        assistant=request.assistant,
        context=request.context,
    )
    result["conversation_id"] = request.conversation_id
    return result


@app.post("/api/command")
def command(request: CommandRequest):
    return _execute_command(request)


@app.post("/api/command/plain")
async def command_plain(request: Request):
    """Cross-origin fallback that accepts a text/plain JSON body.

    This route exists for static hosts such as GitHub Pages. text/plain is a
    CORS-safelisted content type, so browsers can send the POST without an
    OPTIONS preflight. The payload is still validated by the same Pydantic
    CommandRequest model before reaching the engine.
    """
    try:
        raw = await request.body()
        payload = json.loads(raw.decode("utf-8"))
        command_request = CommandRequest.model_validate(payload)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Invalid command payload.") from exc
    return _execute_command(command_request)


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
