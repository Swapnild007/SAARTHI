"""Configuration for hosted resources. Local development uses legacy names."""
from __future__ import annotations

import json
import os
import re
from decimal import Decimal, InvalidOperation
from dataclasses import dataclass
from urllib.parse import urlsplit


def environment() -> str:
    return os.getenv("SAARTHI_ENV", "")


def hosted() -> bool:
    return bool(os.getenv("VERCEL") or os.getenv("VERCEL_ENV")) or environment() not in {"", "local"}


def setting(name: str) -> str:
    scope = environment()
    if hosted():
        if scope not in {"preview", "staging", "production"}:
            return ""
        return os.getenv(f"SAARTHI_{scope.upper()}_{name}", "").strip()
    return os.getenv(f"SAARTHI_{name}", "").strip()


def https_endpoint(value: str) -> bool:
    try:
        parsed = urlsplit(value)
        return bool(parsed.scheme == "https" and parsed.hostname and not (
            parsed.username or parsed.password or parsed.query or parsed.fragment
        ) and parsed.port in (None, 443) and not any(c.isspace() for c in value))
    except ValueError:
        return False


def configured_routes() -> list[dict[str, str]]:
    raw = setting("LLM_ROUTES_JSON")
    if raw:
        try:
            routes = json.loads(raw)
        except ValueError:
            return []
        if not isinstance(routes, list) or not 1 <= len(routes) <= 2:
            return []
    elif not hosted():
        routes = [{
            "name": os.getenv("SAARTHI_LLM_PROVIDER_NAME", "OpenRouter"),
            "url": os.getenv("SAARTHI_LLM_API_URL", "https://openrouter.ai/api/v1"),
            "key": setting("LLM_API_KEY"),
            "model": os.getenv("SAARTHI_LLM_MODEL", "openrouter/free"),
        }]
    else:
        return []
    required = {"name", "url", "key", "model"}
    if any(not isinstance(route, dict) or not all(
        isinstance(route.get(field), str) and route[field].strip() for field in required
    ) or not https_endpoint(route["url"]) for route in routes):
        return []
    if hosted() and any(route["url"].rstrip("/") != "https://openrouter.ai/api/v1" for route in routes):
        return []
    if len({route["name"] for route in routes}) != len(routes):
        return []
    return [{field: route[field].strip() for field in required} for route in routes]


def storage_endpoint() -> tuple[str, str]:
    url = setting("SUPABASE_URL").rstrip("/")
    key = setting("SUPABASE_SERVICE_ROLE_KEY")
    if not hosted():
        return url, key
    project = setting("SUPABASE_PROJECT_REF")
    if not re.fullmatch(r"[a-z0-9]{20}", project) or url != f"https://{project}.supabase.co":
        return "", ""
    return url, key


@dataclass(frozen=True)
class SpendLimits:
    reserve: int
    daily: int
    monthly: int

    @classmethod
    def read(cls, gateway: str = "LLM") -> SpendLimits | None:
        names = (f"{gateway}_TURN_RESERVE_MICRO_USD", "DAILY_BUDGET_MICRO_USD", "MONTHLY_BUDGET_MICRO_USD")
        try:
            reserve, daily, monthly = (int(setting(name)) for name in names)
        except ValueError:
            return None
        if setting(f"{gateway}_HARD_CAP_CONFIRMED") != "true" or not 0 < reserve <= daily <= monthly <= 10**12:
            return None
        return cls(reserve, daily, monthly)


def build_commit() -> str | None:
    value = os.getenv("VERCEL_GIT_COMMIT_SHA") or os.getenv("SAARTHI_COMMIT_SHA", "")
    return value if re.fullmatch(r"[a-f0-9]{40}", value) else None


def upstream_key_ceiling(data: object, maximum_micro_usd: int) -> bool:
    """Accept a lifetime key ceiling within the deployment's worst-case allowance."""
    if not isinstance(data, dict) or data.get("limit_reset") is not None:
        return False
    try:
        limit = Decimal(str(data["limit"]))
        remaining = Decimal(str(data["limit_remaining"]))
        return (limit.is_finite() and remaining.is_finite() and
                0 < remaining <= limit <= Decimal(maximum_micro_usd) / 10**6)
    except (KeyError, ValueError, InvalidOperation):
        return False
