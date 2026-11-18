"""Owner-scoped, opt-in chat access to a dedicated Hermes gateway."""
from __future__ import annotations

import hashlib
import hmac
from urllib.parse import urlsplit

import httpx

from .private_session import Scope
from .deployment import hosted, setting


def configuration(scope: Scope | None) -> tuple[str, str] | None:
    if scope is None or setting("HERMES_VALIDATED_SCOPE") != scope.environment:
        return None
    if hosted() and setting("HERMES_TOOLS_DISABLED_CONFIRMED") != "true":
        return None
    endpoint = setting("HERMES_URL").rstrip("/")
    secret = setting("HERMES_API_KEY")
    try:
        parsed = urlsplit(endpoint)
        if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
                or parsed.path or parsed.query or parsed.fragment
                or not secret or setting("HERMES_ENABLED") != "true"):
            return None
    except ValueError:
        return None
    return endpoint, secret


async def generate(scope: Scope, thread: str, message: str, history: list[dict]) -> dict:
    config = configuration(scope)
    if config is None:
        return failed("hermes_disabled", "Hermes is disabled. Select standard SAARTHI chat.")
    endpoint, secret = config
    session = hmac.new(secret.encode(), f"{scope.environment}:{scope.owner}:{thread}".encode(), hashlib.sha256).hexdigest()
    try:
        async with httpx.AsyncClient(timeout=14.0, follow_redirects=False) as client:
            response = await client.post(
                endpoint + "/v1/chat/completions",
                headers={"Authorization": f"Bearer {secret}", "X-Hermes-Session-Key": session},
                json={"model": "hermes-agent", "stream": False,
                      "messages": [*history, {"role": "user", "content": message}]},
            )
        if response.status_code == 429:
            return failed("provider_rate_limited", "Hermes is rate limited. Try again later or select standard chat.")
        if not response.is_success:
            return failed("hermes_unavailable", "Hermes is unavailable. Standard SAARTHI chat remains available.")
        data = response.json()
        message = data["choices"][0]["message"]
        if message.get("tool_calls") or message.get("function_call"):
            return failed("hermes_tool_response", "Hermes returned an unsupported tool response.")
        reply = message["content"]
        if not isinstance(reply, str) or not reply.strip():
            raise ValueError
    except httpx.TimeoutException:
        return failed("provider_timeout", "Hermes did not respond before its deadline.")
    except (httpx.HTTPError, ValueError, KeyError, TypeError, IndexError):
        return failed("hermes_unavailable", "Hermes returned no usable reply. Try standard chat.")
    return {"ok": True, "provider": "hermes-agent", "reply": reply, "execution": "completed",
            "usage": data.get("usage"), "response_source": "upstream", "verification": {"verified": False}}


def failed(code: str, reply: str) -> dict:
    return {"ok": False, "provider": "hermes-agent", "execution": code, "error_code": code, "reply": reply,
            "verification": {"verified": False}}
