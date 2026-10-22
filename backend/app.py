from __future__ import annotations

import asyncio
import json
import hmac
import os
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal
from urllib.request import Request as UrlRequest, urlopen

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .engine import SaarthiEngine
from .provider_settings import ProviderSelection, selection
from .storage import CloudStore, store_status
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
        "https://saarthi-swapneeldalvi3-1192.vercel.app",
        "https://swapnild007.github.io",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]
)



# Defense-in-depth controls. Production-grade distributed rate limiting should
# also be enforced at the edge/API gateway because serverless instances are ephemeral.
_RATE_LIMIT = max(1, int(os.getenv("SAARTHI_RATE_LIMIT_PER_MINUTE", "60")))
_rate_buckets: dict[str, deque[float]] = defaultdict(deque)


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    # Pydantic errors normally include raw input, which could contain an API key.
    return JSONResponse(status_code=422, content={"detail": [
        {"loc": error["loc"], "msg": error["msg"], "type": error["type"]} for error in exc.errors()
    ]})


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    if request.url.path.startswith("/api/"):
        expected = os.getenv("SAARTHI_ACCESS_TOKEN", "")
        # A configured shared credential/store must never become public by omission.
        private_resources = (
            bool(getattr(getattr(request.app.state, "cloud_store", None), "configured", False))
            or bool(getattr(engine.cloud, "configured", False))
            or os.getenv("SAARTHI_MCP_SERVERS_JSON", "[]").strip() not in {"", "[]"}
        )
        if not expected and private_resources and request.url.path != "/api/health" and request.method != "OPTIONS":
            return JSONResponse(status_code=503, content={"detail": "Private deployment access must be configured before enabling shared services."}, headers={"Cache-Control": "no-store"})
        if expected and request.url.path != "/api/health" and request.method != "OPTIONS":
            supplied = request.headers.get("x-saarthi-access", "")
            if not hmac.compare_digest(supplied, expected):
                return JSONResponse(status_code=401, content={"detail": "Deployment access token required."})
        length = request.headers.get("content-length", "0")
        if length.isdigit() and int(length) > 3_000_000:
            return JSONResponse(status_code=413, content={"detail": "Request exceeds 3 MB limit."})
        now = time.monotonic()
        forwarded = request.headers.get("x-forwarded-for", "") if os.getenv("SAARTHI_TRUST_PROXY_HEADERS") == "true" else ""
        client_id = forwarded.split(",", 1)[0].strip() or (
            request.client.host if request.client else "unknown"
        )
        if len(_rate_buckets) >= 4096 and client_id not in _rate_buckets:
            for identity in list(_rate_buckets):
                if not _rate_buckets[identity] or _rate_buckets[identity][-1] <= now-60:
                    del _rate_buckets[identity]
            if len(_rate_buckets) >= 4096:
                client_id = "overflow"
        bucket = _rate_buckets[client_id]
        cutoff = now - 60.0
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if len(bucket) >= _RATE_LIMIT:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please retry shortly."},
                headers={"Retry-After": "60", "Cache-Control": "no-store"},
            )
        bucket.append(now)

    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN" if request.url.path.startswith("/appforge") else "DENY")
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
    if request.url.path.rstrip("/") == "/appforge":
        response.headers.setdefault("Content-Security-Policy",
            "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
            "frame-src 'self'; connect-src 'self'; img-src 'self' data: blob:; object-src 'none'; "
            "base-uri 'none'; frame-ancestors 'self'; form-action 'self'")
    if request.url.path == "/":
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data: blob:; "
            "media-src 'self' blob:; "
            "connect-src 'self' https://saarthi-swapneeldalvi3-1192.vercel.app https://swapnild007.github.io https://api.open-meteo.com https://api.bigdatacloud.net https://ipwho.is; "
            "frame-src 'self'; object-src 'none'; "
            "base-uri 'self'; "
            "frame-ancestors 'none'; "
            "form-action 'self'",
        )
    return response

from .http_limits import RequestBodyLimit
app.add_middleware(RequestBodyLimit)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS", "DELETE"],
    allow_headers=["Accept", "Content-Type", "Authorization", "X-SAARTHI-Access", "X-AppForge-Build-Key"],
    max_age=600,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

@app.get("/appforge", include_in_schema=False)
def appforge_frontend():
    return FileResponse(PROJECT_ROOT / "appforge" / "index.html")

# Serve the premium static SAARTHI frontend from the same FastAPI application.
# Keeping frontend and API in one ASGI app avoids Vercel routing ambiguity.
for _path_name in ("assets", "scripts", "styles", "config", "appforge"):
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
    session_id: str | None = None
    provider_settings: ProviderSelection | None = None
    context: dict[str, Any] = Field(default_factory=dict)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12000)
    assistant: Assistant = "saarthi"
    conversation_id: str | None = None
    provider_settings: ProviderSelection | None = None
    context: dict[str, Any] = Field(default_factory=dict)


engine = SaarthiEngine()
app.state.saarthi_engine = engine
store = CloudStore()
app.state.cloud_store = store

from .appforge_api import router as appforge_router
app.include_router(appforge_router)


@app.get("/api/health")
def health():
    # Keep infrastructure details out of the public health contract.
    return {
        "ok": True,
        "service": "saarthi-api",
        "architecture": "cloud",
        "engine": "saarthi-runtime-v1",
        "provider_configured": engine.cloud.configured,
        "persistence": store_status(store),
        "rag": __rag_status(),
        "mcp": __mcp_status(),
    }


@app.get("/api/persistence")
def persistence():
    return {"ok": True, **store_status(store)}


@app.get("/api/conversations")
def conversations(session_id: str, limit: int = 50):
    if not store.configured:
        return {"ok": False, "provider": "browser-local", "conversations": []}
    try:
        return {"ok": True, "provider": "supabase-postgrest", "conversations": store.conversations(session_id, limit)}
    except Exception as exc:
        return {"ok": False, "provider": "supabase-postgrest", "conversations": [], "error": str(exc)[:180]}


@app.get("/api/conversations/{conversation_id}/messages")
def conversation_messages(conversation_id: str, session_id: str, limit: int = 100):
    if not store.configured:
        return {"ok": False, "provider": "browser-local", "messages": []}
    try:
        return {"ok": True, "provider": "supabase-postgrest", "messages": store.messages(session_id, conversation_id, limit)}
    except Exception as exc:
        return {"ok": False, "provider": "supabase-postgrest", "messages": [], "error": str(exc)[:180]}


@app.get("/api/memory")
def memory(session_id: str, limit: int = 50):
    if not store.configured:
        return {"ok": False, "provider": "browser-local", "memories": []}
    try:
        return {"ok": True, "provider": "supabase-postgrest", "memories": store.memories(session_id, limit)}
    except Exception as exc:
        return {"ok": False, "provider": "supabase-postgrest", "memories": [], "error": str(exc)[:180]}


@app.post("/api/memory")
async def memory_create(request: Request):
    if not store.configured:
        return {"ok": False, "provider": "browser-local", "saved": False}
    try:
        payload = await request.json()
        session_id = str(payload.get("session_id") or "").strip()
        content = str(payload.get("content") or "").strip()
        if not session_id or not content:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="session_id and content are required")
        row = store.save_memory(session_id, str(payload.get("memory_type") or "general"), content, float(payload.get("importance", 0.5)))
        return {"ok": True, "provider": "supabase-postgrest", "saved": True, "memory": row}
    except Exception as exc:
        return {"ok": False, "provider": "supabase-postgrest", "saved": False, "error": str(exc)[:180]}


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


def __rag_status():
    from .rag import status as rag_status
    return rag_status()

def __mcp_status():
    from .mcp_runtime import status as mcp_status
    return mcp_status()

@app.get("/api/rag/status")
def rag_status_endpoint():
    return {"ok": True, **__rag_status()}

@app.post("/api/knowledge/search")
async def knowledge_search(request: Request):
    from .rag import admin_token_valid, search
    authorization = request.headers.get("authorization", "")
    token = authorization[7:].strip() if authorization.lower().startswith("bearer ") else ""
    if not admin_token_valid(token):
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Knowledge search is not authorized.")
    try:
        payload = await request.json()
        query = str(payload.get("query") or "").strip()
        if not query:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="query is required")
        return {"ok": True, "results": search(query, limit=int(payload.get("limit", 5)),
                                                 collection=str(payload.get("collection") or "default"))}
    except Exception as exc:
        from fastapi import HTTPException
        if isinstance(exc, HTTPException):
            raise
        return {"ok": False, "results": [], "error": str(exc)[:180]}

@app.post("/api/knowledge/ingest")
async def knowledge_ingest(request: Request):
    from .rag import admin_token_valid, ingest_text
    authorization = request.headers.get("authorization", "")
    token = authorization[7:].strip() if authorization.lower().startswith("bearer ") else ""
    if not admin_token_valid(token):
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Knowledge ingestion is not authorized.")
    try:
        payload = await request.json()
        text_value = str(payload.get("text") or "")
        title = str(payload.get("title") or "Untitled document").strip()
        source = str(payload.get("source") or "").strip()
        collection = str(payload.get("collection") or "default").strip()
        attachment = payload.get("attachment")
        if not text_value.strip() and isinstance(attachment, dict):
            from .attachments import inspect_attachment
            parsed = inspect_attachment(attachment)
            if parsed.get("error"):
                from fastapi import HTTPException
                raise HTTPException(status_code=400, detail=str(parsed["error"])[:180])
            text_value = str(parsed.get("text") or "")
            if not text_value and isinstance(parsed.get("workbook"), dict):
                text_value = json.dumps(parsed["workbook"].get("analysis_rows", {}), ensure_ascii=False)
            if not source:
                source = str(parsed.get("name") or attachment.get("name") or "")
            if title == "Untitled document":
                title = str(parsed.get("name") or title)
        if not text_value.strip():
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="Provide text or a supported text/PDF/CSV/JSON/Excel attachment.")
        if len(text_value) > 500000:
            from fastapi import HTTPException
            raise HTTPException(status_code=413, detail="Document exceeds the 500,000-character ingestion limit.")
        return {"ok": True, **ingest_text(text_value, title=title, source=source, collection=collection)}
    except Exception as exc:
        from fastapi import HTTPException
        if isinstance(exc, HTTPException):
            raise
        return {"ok": False, "error": str(exc)[:180]}

@app.get("/api/mcp/status")
def mcp_status_endpoint():
    return {"ok": True, **__mcp_status()}

@app.get("/api/mcp/tools")
def mcp_tools_endpoint(request: Request):
    from .rag import admin_token_valid
    authorization = request.headers.get("authorization", "")
    token = authorization[7:].strip() if authorization.lower().startswith("bearer ") else ""
    if not admin_token_valid(token):
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="MCP tool discovery is not authorized.")
    from .mcp_runtime import list_tools
    tools, errors = list_tools(force_refresh=True)
    return {"ok": True, "tools": [{"name": item["function"]["name"],
            "remote_name": item["_remote_tool"], "server": item["_server"],
            "approved": item.get("_approved", False), "safe_to_call": item.get("_safe_to_call", False),
            "read_only": item.get("_read_only", False),
            "description": item["function"]["description"],
            "input_schema": item["function"]["parameters"]} for item in tools],
            "unavailable_servers": errors}

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
    token = selection.set(request.provider_settings)
    try:
        return _execute_selected_command(request)
    finally:
        selection.reset(token)


def _execute_selected_command(request: CommandRequest) -> dict[str, Any]:
    result = engine.run(
        message=request.message,
        mode=request.mode,
        assistant=request.assistant,
        context=request.context,
    )
    result["conversation_id"] = request.conversation_id
    return result


async def _execute_command_bounded(request: CommandRequest) -> dict[str, Any]:
    """Run the synchronous engine behind an explicit request deadline."""
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_execute_command, request),
            timeout=28.0,
        )
    except asyncio.TimeoutError:
        return {
            "ok": True,
            "run_id": f"timeout-{int(time.time() * 1000)}",
            "assistant": {"id": request.assistant, "name": "Saarthi"},
            "intent": {"name": request.mode, "confidence": 1.0, "reason": "runtime-timeout"},
            "plan": [],
            "orchestration": {},
            "reply": (
                "The cloud model did not return a response before SAARTHI's 28-second deadline. "
                "Please retry once; if it happens again, try a shorter prompt."
            ),
            "provider": "runtime-timeout",
            "route": None,
            "failover": [],
            "usage": None,
            "execution": "timed-out-safely",
            "tool_results": {},
            "verification": {"verified": True, "claims": "request deadline enforced"},
        }


@app.post("/api/command")
async def command(request: CommandRequest):
    return await _execute_command_bounded(request)


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
    return await _execute_command_bounded(command_request)


@app.post("/api/chat")
async def chat(request: ChatRequest):
    command_request = CommandRequest(
        message=request.message,
        mode="chat",
        assistant=request.assistant,
        conversation_id=request.conversation_id,
        context=request.context,
        provider_settings=request.provider_settings,
    )
    return await _execute_command_bounded(command_request)


@app.get("/manifest.webmanifest", include_in_schema=False)
def manifest():
    return FileResponse(PROJECT_ROOT / "manifest.webmanifest", media_type="application/manifest+json")

@app.get("/sw.js", include_in_schema=False)
def service_worker():
    return FileResponse(PROJECT_ROOT / "sw.js", media_type="text/javascript", headers={"Cache-Control": "no-cache"})

@app.get("/api/providers")
def providers():
    from .provider_settings import PROVIDERS
    return {"providers": [{"id": key, "name": item[0]} for key, item in PROVIDERS.items()],
            "server_configured": engine.cloud.configured}

@app.post("/api/providers/validate")
async def validate_provider(payload: ProviderSelection):
    import httpx
    from .provider_settings import PROVIDERS
    if payload.provider == "server":
        return {"ok": engine.cloud.configured, "detail": "Server configuration checked; inference not tested."}
    if not payload.api_key.get_secret_value() or not payload.model:
        return JSONResponse(status_code=400, content={"detail": "Model and API key required."})
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
            response = await client.get(PROVIDERS[payload.provider][1] + "/models", headers={
                "Authorization": "Bearer " + payload.api_key.get_secret_value()})
        if response.status_code != 200:
            return JSONResponse(status_code=400, content={"detail": f"Provider returned HTTP {response.status_code}."})
        ids = {item.get("id") for item in response.json().get("data", []) if isinstance(item, dict)}
        return {"ok": payload.model in ids, "detail": "Key accepted; model listed." if payload.model in ids else "Key accepted; model ID not listed. Check your provider console."}
    except Exception:
        return JSONResponse(status_code=502, content={"detail": "Provider validation unavailable or timed out."})


class ExtractionRequest(BaseModel):
    name: str = Field(max_length=180)
    type: str = Field(default="text/plain", max_length=100)
    data: str = Field(max_length=700000)

@app.post("/api/knowledge/extract")
async def knowledge_extract(payload: ExtractionRequest):
    from .attachments import inspect_attachment
    parsed = await asyncio.to_thread(inspect_attachment, payload.model_dump())
    if parsed.get("error"):
        return JSONResponse(status_code=400, content={"detail": str(parsed["error"])[:180]})
    return {"text": str(parsed.get("text") or "")[:100000], "name": payload.name}


class MCPInvocation(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    arguments: dict[str, Any] = Field(default_factory=dict)
    confirmed: bool = False

@app.post("/api/mcp/invoke")
async def mcp_invoke(payload: MCPInvocation, request: Request):
    from .rag import admin_token_valid
    from .mcp_runtime import call_tool
    token = request.headers.get("authorization", "").removeprefix("Bearer ")
    if not admin_token_valid(token):
        return JSONResponse(status_code=401, content={"detail": "MCP invocation is not authorized."})
    try:
        return {"ok": True, **await asyncio.to_thread(call_tool, payload.name, payload.arguments, confirmed=payload.confirmed)}
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except Exception:
        return JSONResponse(status_code=502, content={"detail": "Remote tool unavailable or failed."})


@app.post("/api/command/stream")
async def command_stream(payload: CommandRequest, request: Request):
    from fastapi.responses import StreamingResponse
    from .streaming import sink
    loop = asyncio.get_running_loop()
    queue = asyncio.Queue(maxsize=1024)
    active = True
    def emit(text):
        def enqueue():
            if active and not queue.full():
                queue.put_nowait({"type": "delta", "text": text})
        loop.call_soon_threadsafe(enqueue)
    async def events():
        nonlocal active
        token = sink.set(emit)
        task = asyncio.create_task(_execute_command_bounded(payload))
        try:
            while not task.done() or not queue.empty():
                if await request.is_disconnected():
                    break
                try:
                    item = await asyncio.wait_for(queue.get(), .2)
                    yield "data: " + json.dumps(item) + "\n\n"
                except asyncio.TimeoutError:
                    continue
            if not await request.is_disconnected():
                result = await task
                yield "data: " + json.dumps({"type": "result", "result": result}) + "\n\n"
        except Exception:
            yield "data: " + json.dumps({"type": "error", "message": "Request failed. Check Settings and try again."}) + "\n\n"
        finally:
            active = False
            sink.reset(token)
            if not task.done():
                task.cancel()
    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})
