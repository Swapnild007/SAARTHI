from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import platform
import re
from contextlib import suppress
from uuid import UUID, uuid4

import httpx
import os
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal
from urllib.request import Request as UrlRequest, urlopen

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.requests import ClientDisconnect
from .execution import run_turn
from .deployment import SpendLimits, build_commit, hosted, setting, route_diagnostics, free_only_routes
from decimal import Decimal, InvalidOperation, ROUND_CEILING
from . import hermes_bridge
from dataclasses import replace
import secrets
from .passwords import hash_password, valid_hash
from .onboarding import GRANT_COOKIE, GRANT_TTL, database_auth, verify_deployment_access, authorization_digest
from .private_session import COOKIE, TTL, Scope
from pydantic import BaseModel, Field

from .engine import SaarthiEngine
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

# Defense-in-depth controls. Production-grade distributed rate limiting should
# also be enforced at the edge/API gateway because serverless instances are ephemeral.
_RATE_LIMIT = max(1, int(os.getenv("SAARTHI_RATE_LIMIT_PER_MINUTE", "60")))
_rate_buckets: dict[str, deque[float]] = defaultdict(deque)


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    request.state.started_at = time.monotonic()
    if request.url.path.startswith("/api/") and request.url.path not in {"/api/health", "/api/onboarding"}:
        scope = Scope.read()
        if scope is None or str(request.base_url).rstrip("/") != scope.origin:
            return api_error(503, "configuration_unavailable", "This deployment is not configured for private chat.")
        if request.method not in {"GET", "HEAD"}:
            if request.headers.get("origin", scope.origin) != scope.origin:
                return api_error(403, "origin_denied", "This origin is not permitted.")
        onboarding = request.url.path in {"/api/onboarding/verify", "/api/onboarding/password"}
        if database_auth():
            try:
                async with asyncio.timeout(2.5):
                    await store.check_scope(scope.environment)
                    credential = await store.owner_password(scope.owner)
                if credential:
                    if not valid_hash(credential):
                        return api_error(503, "owner_unavailable", "Owner sign-in is temporarily unavailable.")
                    scope = replace(scope, password=credential)
            except (TimeoutError, RuntimeError, httpx.HTTPError, ValueError, KeyError):
                return api_error(503, "onboarding_unavailable", "Owner setup needs the connected conversation database.")
        login = request.url.path == "/api/session/login"
        if not login and not onboarding and not scope.authenticated(request.cookies.get(COOKIE, "")):
            return api_error(401, "authentication_required", "Sign in to continue.")
        if request.method not in {"GET", "HEAD"}:
            maximum = 4096 if login or onboarding else 2_500_000
            chunks = []
            size = 0
            try:
                async with asyncio.timeout(3):
                    async for chunk in request.stream():
                        size += len(chunk)
                        if size > maximum:
                            return api_error(413, "request_too_large", "The request exceeds the upload limit.")
                        chunks.append(chunk)
            except (TimeoutError, ClientDisconnect):
                return api_error(408, "request_interrupted", "The request body did not arrive in time.")
            request._body = b"".join(chunks)  # BaseHTTPMiddleware forwards this cached body.
        client_id = "login" if login or onboarding else scope.owner
        bucket = _rate_buckets[client_id]
        now = time.monotonic()
        while bucket and bucket[0] <= now - 60:
            bucket.popleft()
        if len(bucket) >= (min(10, _RATE_LIMIT) if login or onboarding else _RATE_LIMIT):
            response = api_error(429, "rate_limited", "Too many requests. Wait one minute and try again.")
            response.headers["Retry-After"] = "60"
            return response
        bucket.append(now)
        request.state.scope = scope

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
    if request.url.path in {"/", "/command-center.html"}:
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data: blob:; "
            "media-src 'self' blob:; "
            "connect-src 'self' https://api.open-meteo.com https://api.bigdatacloud.net https://ipwho.is; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "frame-ancestors 'none'; "
            "form-action 'self'",
        )
    return response

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Serve the premium static SAARTHI frontend from the same FastAPI application.
# Keeping frontend and API in one ASGI app avoids Vercel routing ambiguity.
for _path_name in ("assets", "scripts", "styles"):
    _path = PROJECT_ROOT / _path_name
    if _path.is_dir():
        app.mount(f"/{_path_name}", StaticFiles(directory=str(_path)), name=_path_name)


@app.get("/", include_in_schema=False)
def frontend():
    return FileResponse(PROJECT_ROOT / "index.html")

@app.get("/command-center.html", include_in_schema=False)
def command_center():
    return FileResponse(PROJECT_ROOT / "command-center.html")


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
    conversation_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]{1,100}$")
    turn_id: UUID | None = None
    engine: Literal["default", "hermes"] = "default"
    context: dict[str, Any] = Field(default_factory=dict)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12000)
    assistant: Assistant = "saarthi"
    conversation_id: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)


engine = SaarthiEngine()
store = CloudStore()


def api_error(status: int, code: str, detail: str) -> JSONResponse:
    return JSONResponse({"ok": False, "error_code": code, "detail": detail},
                        status_code=status, headers={"Cache-Control": "no-store"})


@app.exception_handler(RequestValidationError)
async def invalid_request(request: Request, error: RequestValidationError):
    return api_error(422, "invalid_input", "Check the submitted fields and try again.")


class LoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=512)


class OwnerVerification(BaseModel):
    management_token: str = Field(min_length=1, max_length=2048)
    intent: Literal["setup", "recover"] = "setup"


class OwnerPassword(BaseModel):
    password: str = Field(min_length=24, max_length=512)


@app.get("/api/onboarding")
async def onboarding_status():
    scope = Scope.read()
    if scope and not database_auth() and scope.password:
        return {"ok": True, "stage": "sign_in", "message": "Sign in with your existing owner password."}
    if scope is None or not database_auth():
        return {"ok": False, "stage": "connection_required",
                "message": "Connect the conversation database and deployment access to activate owner setup."}
    try:
        async with asyncio.timeout(2.5):
            await store.check_scope(scope.environment)
            credential = await store.owner_password(scope.owner)
        configured = bool(credential or bool(scope.password))
        return {"ok": True, "stage": "sign_in" if configured else "verify_owner",
                "message": "Sign in or verify deployment ownership to recover access." if configured
                           else "Verify Vercel project access, then create your password."}
    except (TimeoutError, RuntimeError, httpx.HTTPError, ValueError, KeyError):
        return {"ok": False, "stage": "connection_required",
                "message": "The conversation database is not connected yet. Connect Supabase to finish activation."}


@app.post("/api/onboarding/verify")
async def onboarding_verify(request: Request, payload: OwnerVerification):
    if not database_auth():
        return api_error(503, "setup_unavailable", "Browser owner setup is not activated.")
    scope = request.state.scope
    if payload.intent == "setup" and bool(scope.password):
        return api_error(409, "already_initialized", "Owner setup is complete. Use account recovery.")
    try:
        async with asyncio.timeout(18):
            if not await store.claim_login(scope.owner):
                return api_error(429, "rate_limited", "Wait one minute before verifying again.")
            if not await verify_deployment_access(payload.management_token):
                return api_error(403, "management_denied", "Vercel did not authorize management access to this project.")
            token = secrets.token_urlsafe(32)
            legacy = hashlib.sha256(scope.password.encode()).hexdigest() if scope.password else ""
            issued = await store.issue_owner_grant(scope.owner, authorization_digest(scope.environment, scope.origin, token),
                                                   payload.intent, legacy)
        if not issued:
            return api_error(409, "setup_changed", "Owner setup changed. Start verification again.")
    except (TimeoutError, RuntimeError, httpx.HTTPError, ValueError, KeyError):
        return api_error(503, "verification_unavailable", "Ownership verification could not finish. Retry shortly.")
    response = JSONResponse({"ok": True, "expires_in_seconds": GRANT_TTL})
    response.set_cookie(GRANT_COOKIE, token, max_age=GRANT_TTL, httponly=True,
                        secure=scope.origin.startswith("https:"), samesite="strict", path="/api/onboarding")
    return response


@app.post("/api/onboarding/password")
async def onboarding_password(request: Request, payload: OwnerPassword):
    scope = request.state.scope
    token = request.cookies.get(GRANT_COOKIE, "")
    if not database_auth() or not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
        return api_error(403, "setup_authorization_required", "Verify deployment ownership before choosing a password.")
    try:
        encoded = await asyncio.to_thread(hash_password, payload.password)
        legacy = hashlib.sha256(scope.password.encode()).hexdigest() if scope.password else ""
        async with asyncio.timeout(2.5):
            saved = await store.complete_owner_setup(scope.owner, authorization_digest(scope.environment, scope.origin, token),
                                                     encoded, legacy)
        if not saved:
            return api_error(403, "setup_expired", "Setup authorization expired or was already used. Verify again.")
    except (TimeoutError, RuntimeError, httpx.HTTPError, ValueError):
        return api_error(503, "setup_unavailable", "Password could not be saved. Start verification again.")
    response = JSONResponse({"ok": True})
    response.delete_cookie(GRANT_COOKIE, path="/api/onboarding")
    response.set_cookie(COOKIE, replace(scope, password=encoded).issue(), max_age=TTL, httponly=True,
                        secure=scope.origin.startswith("https:"), samesite="strict", path="/")
    return response


@app.post("/api/session/login")
async def login(request: Request, payload: LoginRequest):
    scope = request.state.scope
    if not scope.password:
        return api_error(409, "owner_setup_required", "Create your owner password first.")
    if hosted():
        await scoped_store(request)
        try:
            async with asyncio.timeout(2.5):
                allowed = await store.claim_login(scope.owner)
        except (TimeoutError, RuntimeError, httpx.HTTPError, ValueError):
            return api_error(503, "login_unavailable", "Sign-in is temporarily unavailable.")
        if not allowed:
            return api_error(429, "rate_limited", "Too many sign-in attempts. Wait one minute.")
    if not await asyncio.to_thread(scope.verify_password, payload.password):
        return api_error(401, "authentication_failed", "Sign-in failed.")
    response = JSONResponse({"ok": True})
    response.set_cookie(COOKIE, scope.issue(), max_age=TTL, httponly=True,
                        secure=scope.origin.startswith("https:"), samesite="strict", path="/")
    return response


@app.post("/api/session/logout")
def logout():
    response = JSONResponse({"ok": True})
    response.delete_cookie(COOKIE, path="/")
    return response


@app.get("/api/session")
def session_status(request: Request):
    return {"ok": True, "authenticated": True, "expires_in_max_seconds": TTL}


@app.get("/api/health")
async def health():
    scope = Scope.read()
    owner_ready = bool(scope and scope.password)
    if scope and database_auth():
        try:
            async with asyncio.timeout(2.5):
                await store.check_scope(scope.environment)
                credential = await store.owner_password(scope.owner)
            owner_ready = bool(credential and valid_hash(credential) or scope.password)
        except (TimeoutError, RuntimeError, httpx.HTTPError, ValueError, KeyError):
            owner_ready = False
    provider_ready = engine.cloud.configured
    provider_configuration = route_diagnostics()
    spend_ready = free_only_routes(engine.cloud.routes) or SpendLimits.read() is not None
    problems = []
    if scope is None:
        problems.append("private_scope_unconfigured")
    elif not owner_ready:
        problems.append("owner_setup_required")
    if not store.configured:
        problems.append("persistence_unconfigured")
    if not provider_ready:
        problems.append("provider_unconfigured")
    if hosted() and not spend_ready:
        problems.append("spend_controls_unconfigured")
    return {
        "ok": scope is not None and (not hosted() or not problems),
        "configuration_issues": problems,
        "owner_configured": owner_ready,
        "service": "saarthi-api",
        "environment": scope.environment if scope else (os.getenv("VERCEL_ENV") or "unconfigured"),
        "commit": (scope.commit or build_commit()) if scope else build_commit(),
        "python": platform.python_version(),
        "provider_configured": engine.cloud.configured,
        "provider_configuration": provider_configuration,
        "persistence": store_status(store),
        "rag": __rag_status(),
        "mcp": __mcp_status(),
        "hermes": {"enabled": bool(hermes_bridge.configuration(scope)) and (not hosted() or SpendLimits.read("HERMES") is not None)},
    }


async def scoped_store(request: Request) -> Scope:
    scope = request.state.scope
    try:
        async with asyncio.timeout(2.5):
            await store.check_scope(scope.environment)
    except (TimeoutError, RuntimeError, httpx.HTTPError, ValueError):
        raise HTTPException(503, "Conversation storage is unavailable for this deployment.") from None
    return scope


@app.get("/api/persistence")
async def persistence(request: Request):
    await scoped_store(request)
    return {"ok": True, **store_status(store)}


@app.get("/api/conversations")
async def conversations(request: Request, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)):
    scope = await scoped_store(request)
    try:
        rows = await store.recovery_threads(scope.owner, offset, limit)
    except (RuntimeError, httpx.HTTPError, ValueError):
        return api_error(503, "storage_unavailable", "Conversation list could not be read.")
    return {"ok": True, "conversations": rows, "next_offset": offset + len(rows) if len(rows) == limit else None}


def valid_thread(thread: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", thread):
        raise HTTPException(400, "Invalid conversation identifier.")
    return thread


@app.get("/api/conversations/{conversation_id}/messages")
async def conversation_messages(request: Request, conversation_id: str,
                                after: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)):
    thread = valid_thread(conversation_id)
    scope = await scoped_store(request)
    try:
        rows = await store.recovery_turns(scope.owner, thread, after, limit)
    except (RuntimeError, httpx.HTTPError, ValueError):
        return api_error(503, "storage_unavailable", "Conversation could not be read.")
    for row in rows:
        if row["state"] == "pending" and datetime.fromisoformat(row["created_at"]) < datetime.now(timezone.utc) - timedelta(seconds=60):
            row["state"] = "interrupted"
    return {"ok": True, "turns": rows, "next_after": rows[-1]["seq"] if len(rows) == limit else None}


class ThreadUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=200)


@app.patch("/api/conversations/{conversation_id}")
@app.delete("/api/conversations/{conversation_id}")
async def modify_conversation(request: Request, conversation_id: str, payload: ThreadUpdate | None = None):
    thread = valid_thread(conversation_id)
    scope = await scoped_store(request)
    title = payload.title.strip() if payload and request.method == "PATCH" else None
    if request.method == "PATCH" and not title:
        return api_error(400, "invalid_title", "Enter a conversation title.")
    try:
        changed = await store.update_thread(scope.owner, thread, title)
    except (RuntimeError, httpx.HTTPError, ValueError):
        return api_error(503, "storage_unavailable", "Conversation could not be updated.")
    if not changed:
        return api_error(404, "conversation_unavailable", "Conversation unavailable.")
    return {"ok": True}


@app.get("/api/memory")
@app.post("/api/memory")
def memory():
    return api_error(503, "memory_disabled", "Standalone saved facts are disabled in this release candidate.")


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
    return {"configured": False, "reason": "disabled_pending_validation"}


def __mcp_status():
    return {"configured": False, "reason": "disabled_pending_validation"}


@app.get("/api/rag/status")
def rag_status_endpoint():
    return __rag_status()


@app.get("/api/mcp/status")
def mcp_status_endpoint():
    return __mcp_status()


@app.post("/api/knowledge/search")
@app.post("/api/knowledge/ingest")
@app.get("/api/mcp/tools")
def unavailable_tools():
    return api_error(503, "integration_disabled", "This integration is disabled pending staging validation.")


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

    route = provider.routes[0]
    base_url = route["url"].rstrip("/")
    if base_url != "https://openrouter.ai/api/v1":
        return {"ok": False, "source": "unavailable", "reason": "usage_adapter_unsupported"}
    key = route["key"]
    result: dict[str, Any] = {
        "ok": True,
        "source": "openrouter-key",
        "provider": "OpenRouter",
        "analytics_configured": bool(setting("OPENROUTER_MANAGEMENT_KEY")),
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
        result["key_error"] = "Usage provider could not be reached."

    management_key = setting("OPENROUTER_MANAGEMENT_KEY")
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
            result["analytics_error"] = "Usage analytics could not be loaded."

    return result



COMMAND_DEADLINE = 27.0
PERSISTENCE_RESERVE = 3.0
logger = logging.getLogger(__name__)


def failure(code: str, reply: str) -> dict:
    return {"ok": False, "execution": code, "error_code": code, "reply": reply,
            "verification": {"verified": False}}


def bound_context(raw: dict) -> dict:
    context = {key: value[:128] for key, value in raw.items()
               if key in {"timezone", "locale", "client_time", "industry"} and isinstance(value, str)}
    files = raw.get("attachments", [])
    if not isinstance(files, list) or len(files) > 8:
        raise HTTPException(413, "Too many attachments.")
    if any(not isinstance(item, dict) or not isinstance(item.get("data"), str) for item in files):
        raise HTTPException(400, "Invalid attachment metadata.")
    if sum(len(item["data"]) for item in files) > 2_100_000:
        raise HTTPException(413, "Attachments exceed the upload limit.")
    context["attachments"] = [
        {key: item[key] for key in ("name", "type", "data") if isinstance(item.get(key), str)}
        for item in files
    ]
    return context


async def run_hermes(scope: Scope, thread: str, message: str, conversation: list[dict], budget: float):
    async with asyncio.timeout(budget):
        return await hermes_bridge.generate(scope, thread, message, conversation)


async def wait_for_disconnect(request: Request) -> None:
    while not await request.is_disconnected():
        await asyncio.sleep(0.15)


async def wait_for_durable_cancellation(owner: str, turn: str) -> None:
    while True:
        await asyncio.sleep(1)
        try:
            async with asyncio.timeout(1.5):
                row = await store.turn_result(owner, turn)
        except (TimeoutError, RuntimeError, httpx.HTTPError, ValueError):
            continue
        if row is None or row["state"] == "cancelled":
            return


@app.post("/api/turns/{turn_id}/cancel")
async def cancel_turn(request: Request, turn_id: UUID):
    scope = await scoped_store(request)
    turn = str(turn_id)
    terminal = {**failure("cancelled", "This turn was cancelled."), "turn_id": turn}
    try:
        async with asyncio.timeout(2.5):
            if await store.finish_turn(scope.owner, turn, "cancelled", terminal):
                return {"ok": True, "execution": "cancelled"}
            row = await store.turn_result(scope.owner, turn)
    except (TimeoutError, RuntimeError, httpx.HTTPError, ValueError):
        return api_error(503, "storage_unavailable", "Cancellation could not be confirmed.")
    if row and row["state"] == "cancelled":
        return {"ok": True, "execution": "cancelled"}
    return api_error(409, "turn_unavailable", "The turn is unavailable or already finished.")


def reported_cost(usage: object) -> int | None:
    if not isinstance(usage, dict) or not isinstance(usage.get("cost"), (int, float, str)):
        return None
    try:
        value = Decimal(str(usage["cost"]))
        if value.is_finite() and 0 <= value <= 10**6:
            return int((value * 10**6).to_integral_value(rounding=ROUND_CEILING))
    except (ValueError, InvalidOperation):
        pass
    return None


async def _execute_command_bounded(request: Request, payload: CommandRequest):
    started = request.state.started_at
    scope = request.state.scope
    context = bound_context(payload.context)
    await scoped_store(request)
    if payload.mode in {"remember", "task", "tasks", "remind", "workflow", "workflows"}:
        return failure("action_unavailable", "This command is disabled until its storage or scheduler is verified. Standard chat remains available.")
    if payload.engine == "hermes" and context["attachments"]:
        raise HTTPException(400, "Hermes attachments are unavailable. Select standard chat to send files.")
    if payload.assistant == "research":
        context["research_web_search"] = False
    thread = payload.conversation_id or str(uuid4())
    turn = str(payload.turn_id or uuid4())
    identity = {"turn_id": turn, "conversation_id": thread}
    fingerprint = hashlib.sha256(json.dumps(
        [payload.message, payload.mode, payload.assistant, payload.engine, context["attachments"]],
        sort_keys=True, ensure_ascii=False
    ).encode()).hexdigest()
    spend = None
    if hosted():
        if payload.engine == "hermes" and not hermes_bridge.configuration(scope):
            return {**failure("hermes_disabled", "Hermes is disabled. Select standard SAARTHI chat."), **identity}
        if payload.engine == "default" and not engine.cloud.configured:
            diagnostics = route_diagnostics()
            logger.warning("provider_configuration_rejected %s", diagnostics)
            rules = ", ".join(error["rule"] for error in diagnostics["validation_errors"])
            return {**failure("provider_unconfigured", "Model configuration is invalid (" + rules + ")."),
                    **identity, "configuration": diagnostics}
        free_chat = payload.engine == "default" and free_only_routes(engine.cloud.routes)
        spend = None if free_chat else SpendLimits.read("HERMES" if payload.engine == "hermes" else "LLM")
        if not free_chat and spend is None:
            return {**failure("budget_unconfigured", "Provider spending controls are unavailable."), **identity}
    try:
        async with asyncio.timeout(2.5):
            arguments = (scope.owner, thread, turn, payload.message, fingerprint, scope.daily_turns)
            reservation = await store.admit_turn(*arguments, spend) if spend else await store.begin_turn(*arguments)
    except (TimeoutError, RuntimeError, httpx.HTTPError, ValueError):
        return {**failure("storage_unavailable", "Could not confirm the turn was saved. Retry this same turn."), **identity}
    decision = reservation.get("decision")
    if reservation.get("result"):
        return {**reservation["result"], **identity}
    if decision != "started":
        code = {"busy": "turn_pending", "pending": "turn_pending", "conflict": "turn_conflict", "quota": "quota_exceeded", "budget": "budget_exceeded"}.get(decision, "storage_unavailable")
        return {**failure(code, {
            "turn_pending": "A turn is still running. Check history and try again shortly.",
            "turn_conflict": "This turn identifier already belongs to a different submission.",
            "quota_exceeded": "The daily request quota has been reached.",
            "budget_exceeded": "The configured provider spending allowance has been reached.",
        }.get(code, "Conversation storage is unavailable.")), **identity}

    result = failure("runtime_failed", "The chat runtime could not complete. Start a new turn to try again.")
    state = "failed"
    diagnostic = {"intake_and_reservation": round((time.monotonic() - started) * 1000, 2)}
    worker = disconnect = durable_cancel = None
    try:
        try:
            async with asyncio.timeout(2.5):
                prior = await store.recent_turns(scope.owner, thread)
        except (TimeoutError, RuntimeError, httpx.HTTPError, ValueError):
            result = failure("storage_unavailable", "Could not load model context. Start a new turn to try again.")
        else:
            diagnostic["history_read"] = round((time.monotonic() - started) * 1000 - diagnostic["intake_and_reservation"], 2)
            context["conversation"] = [
                {"role": role, "content": content[:4000]} for row in reversed(prior)
                for role, content in (("user", row["message"]), ("assistant", row["result"]["reply"]))
            ]
            budget = COMMAND_DEADLINE - PERSISTENCE_RESERVE - (time.monotonic() - started)
            if budget <= 0:
                raise TimeoutError
            if payload.engine == "hermes":
                worker = asyncio.create_task(run_hermes(scope, thread, payload.message, context["conversation"], budget))
            else:
                worker = asyncio.create_task(run_turn({
                    "message": payload.message, "mode": payload.mode, "assistant": payload.assistant, "context": context,
                }, budget))
            disconnect = asyncio.create_task(wait_for_disconnect(request))
            durable_cancel = asyncio.create_task(wait_for_durable_cancellation(scope.owner, turn))
            finished, _ = await asyncio.wait({worker, disconnect, durable_cancel}, return_when=asyncio.FIRST_COMPLETED)
            if durable_cancel in finished:
                result = failure("cancelled", "This turn was cancelled.")
                state = "cancelled"
            elif disconnect in finished:
                result = failure("cancelled", "The client disconnected.")
                state = "cancelled"
            else:
                result = worker.result()
                state = "completed" if result.get("ok") else "failed"
                if result.get("execution") == "degraded":
                    result["verification"]["verified"] = False
    except TimeoutError:
        result = failure("deadline_exceeded", "The request exceeded the runtime deadline. Start a new turn to try again.")
    except (ValueError, RuntimeError, OSError, KeyError, TypeError):
        logger.warning("turn_worker_failure", extra={"turn_id": turn})
    except asyncio.CancelledError:
        result = failure("cancelled", "Execution was cancelled.")
        state = "cancelled"
        raise
    finally:
        for task in (worker, disconnect, durable_cancel):
            if task is not None:
                task.cancel()
                with suppress(asyncio.CancelledError, Exception):
                    await task
        result.update(identity)
        diagnostic.update(result.get("timings_ms", {}))
        result["timings_ms"] = diagnostic
        try:
            persistence_started = time.monotonic()
            async with asyncio.timeout(PERSISTENCE_RESERVE - 0.25):
                reported = reported_cost(result.get("usage")) if spend else None
                if reported is not None:
                    try:
                        async with asyncio.timeout(0.4):
                            await store.report_cost(scope.owner, turn, reported)
                    except (TimeoutError, RuntimeError, httpx.HTTPError, ValueError):
                        logger.warning("cost_report_unavailable", extra={"turn_id": turn})
                recorded = await store.finish_turn(scope.owner, turn, state, result)
                if not recorded:
                    terminal = await store.turn_result(scope.owner, turn)
                    if terminal and terminal["result"]:
                        result = {**terminal["result"], **identity}
                    else:
                        result = {**failure("storage_conflict", "This turn is no longer pending. Reopen history to check its status."), **identity}
        except (TimeoutError, RuntimeError, httpx.HTTPError, ValueError):
            result = {**failure("storage_unavailable", "Could not confirm the result was saved. Retry this same turn."), **identity}
        logger.info("turn_finished", extra={"turn_id": turn, "status": result.get("execution"),
                    "timings_ms": {**diagnostic, "persistence": round((time.monotonic() - persistence_started) * 1000, 2)}})
    return result


@app.post("/api/command")
async def command(request: Request, payload: CommandRequest):
    return await _execute_command_bounded(request, payload)


@app.post("/api/command/plain")
async def command_plain(request: Request):
    try:
        payload = CommandRequest.model_validate_json(await request.body())
    except ValueError:
        return api_error(400, "invalid_payload", "Invalid command payload.")
    return await _execute_command_bounded(request, payload)


@app.post("/api/chat")
async def chat(request: Request, payload: CommandRequest):
    return await _execute_command_bounded(request, payload.model_copy(update={"mode": "chat"}))
