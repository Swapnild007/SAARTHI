"""Opt-in, server-to-server Hermes Agent integration for SAARTHI.

Never expose the Hermes gateway token or agent tools to the browser.
This router is disabled until both the bridge and caller secrets are configured.
"""
from __future__ import annotations

import asyncio
import json
import os
import secrets
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/hermes", tags=["Hermes integration"])


class HermesMessage(BaseModel):
    message: str = Field(min_length=1, max_length=12000)
    conversation_id: str | None = Field(default=None, max_length=128)


def _config():
    enabled = os.getenv("SAARTHI_HERMES_ENABLED", "").lower() == "true"
    endpoint = os.getenv("SAARTHI_HERMES_URL", "http://127.0.0.1:8642").rstrip("/")
    gateway_key = os.getenv("SAARTHI_HERMES_API_KEY", "")
    caller_key = os.getenv("SAARTHI_HERMES_BRIDGE_KEY", "")
    parsed = urlparse(endpoint)
    local = parsed.hostname in ("localhost", "127.0.0.1", "::1")
    valid_url = (parsed.scheme == "https" or (parsed.scheme == "http" and local)) and bool(parsed.hostname) and not parsed.username and not parsed.password and not parsed.query and not parsed.fragment
    return enabled and bool(gateway_key) and bool(caller_key) and valid_url, endpoint, gateway_key, caller_key


def _request(endpoint, key, message, conversation_id):
    headers = {"Authorization": "Bearer " + key, "Content-Type": "application/json"}
    if conversation_id:
        headers["X-Hermes-Session-Key"] = conversation_id
    payload = json.dumps({"model": "hermes-agent", "messages": [{"role": "user", "content": message}], "stream": False}).encode()
    req = Request(endpoint + "/v1/chat/completions", data=payload, headers=headers, method="POST")
    with urlopen(req, timeout=22) as response:
        if response.status != 200:
            raise RuntimeError("Hermes returned a non-success status")
        data = json.loads(response.read(2_000_000))
    choices = data.get("choices", [])
    reply = choices[0].get("message", {}).get("content") if choices else None
    if not isinstance(reply, str) or not reply.strip():
        raise ValueError("Hermes returned no text")
    return {"ok": True, "provider": "hermes-agent", "reply": reply, "conversation_id": conversation_id}


@router.get("/status")
def status():
    configured, _, _, _ = _config()
    return {"enabled": configured, "provider": "hermes-agent"}


@router.post("/chat")
async def chat(payload: HermesMessage, authorization: str | None = Header(default=None)):
    configured, endpoint, key, caller_key = _config()
    if not configured:
        raise HTTPException(status_code=503, detail="Hermes integration is disabled or not configured")
    supplied = authorization[7:] if authorization and authorization.lower().startswith("bearer ") else ""
    if not secrets.compare_digest(supplied, caller_key):
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_request, endpoint, key, payload.message, payload.conversation_id),
            timeout=25,
        )
    except (HTTPError, URLError, TimeoutError, asyncio.TimeoutError, ValueError, RuntimeError, json.JSONDecodeError):
        raise HTTPException(status_code=502, detail="Hermes backend unavailable or returned an invalid response")
