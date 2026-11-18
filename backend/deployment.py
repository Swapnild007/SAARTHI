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


OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1"
MODEL_PATTERN = r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}"


def free_route(route: dict[str, str]) -> bool:
    model = route.get("model", "")
    return (route.get("url", "").rstrip("/") == OPENROUTER_ENDPOINT
            and (model == "openrouter/free" or "/" in model and model.endswith(":free")))


def free_only_routes(routes: list[dict[str, str]]) -> bool:
    return bool(routes) and all(free_route(route) for route in routes)


def parse_route_document(raw: str) -> tuple[object, str, list[dict]]:
    """Accept defined copy/paste wrappers, with strict JSON inside each wrapper."""
    value = raw.strip()
    document_format = "json"
    assignment = re.match(r"^(?:export\s+)?SAARTHI_(?:(?:PREVIEW|STAGING)_)?LLM_ROUTES_JSON\s*=\s*", value)
    if assignment:
        value = value[assignment.end():].strip()
        document_format = "environment_assignment"
    fence = chr(96) * 3
    if value.startswith(fence + "json\n") and value.endswith("\n" + fence):
        value = value[len(fence + "json\n"):-len("\n" + fence)].strip()
        document_format = "fenced_json"
    if value.startswith("'") and value.endswith("'"):
        value = value[1:-1]
        document_format = "quoted_json"
    if re.fullmatch(r"sk-or-v1-[a-fA-F0-9]{64}", value):
        return [{"url": OPENROUTER_ENDPOINT, "key": value, "model": "openrouter/free"}], "free_key_only", []
    try:
        document = json.loads(value)
        if isinstance(document, str):
            document = json.loads(document)
            document_format = "encoded_json"
        return document, document_format, []
    except json.JSONDecodeError as error:
        return None, document_format, [{"rule": "invalid_json", "line": error.lineno,
                                       "column": error.colno, "position": error.pos}]


def route_configuration() -> tuple[list[dict[str, str]], list[dict]]:
    """Validate routes and return fixed rule names, never input values."""
    raw = setting("LLM_ROUTES_JSON")
    if raw:
        routes, _, parse_errors = parse_route_document(raw)
        if parse_errors:
            return [], parse_errors
        # A single route object is equivalent to a one-element route list.
        if isinstance(routes, dict):
            routes = [routes]
        if not isinstance(routes, list) or not 1 <= len(routes) <= 2:
            return [], [{"rule": "route_count_or_type"}]
    elif not hosted():
        routes = [{
            "name": os.getenv("SAARTHI_LLM_PROVIDER_NAME", "OpenRouter"),
            "url": os.getenv("SAARTHI_LLM_API_URL", OPENROUTER_ENDPOINT),
            "key": setting("LLM_API_KEY"),
            "model": os.getenv("SAARTHI_LLM_MODEL", "openrouter/free"),
        }]
    else:
        return [], [{"rule": "scoped_routes_missing"}]

    errors = []
    normalized = []
    for index, route in enumerate(routes):
        if not isinstance(route, dict):
            errors.append({"rule": "route_not_object", "route": index})
            continue
        if set(route) - {"name", "url", "key", "model"}:
            errors.append({"rule": "unsupported_route_fields", "route": index})
        for field in ("url", "key", "model"):
            if not isinstance(route.get(field), str) or not route[field].strip():
                errors.append({"rule": "missing_or_invalid_field", "route": index, "field": field})
        if "name" in route and (not isinstance(route["name"], str) or not route["name"].strip()):
            errors.append({"rule": "missing_or_invalid_field", "route": index, "field": "name"})
        if any(error.get("route") == index for error in errors):
            continue
        candidate = {field: route[field].strip() for field in ("url", "key", "model")}
        candidate["name"] = route.get("name", f"route-{index + 1}").strip()
        candidate["url"] = candidate["url"].rstrip("/")
        if not https_endpoint(candidate["url"]) or (hosted() and candidate["url"] != OPENROUTER_ENDPOINT):
            errors.append({"rule": "endpoint_not_allowed", "route": index, "field": "url"})
        if not re.fullmatch(MODEL_PATTERN, candidate["model"]):
            errors.append({"rule": "invalid_model_identifier", "route": index, "field": "model"})
        normalized.append(candidate)
    if errors:
        return [], errors
    if len({route["name"] for route in normalized}) != len(normalized):
        return [], [{"rule": "duplicate_route_names"}]
    if any(free_route(route) for route in normalized) and not free_only_routes(normalized):
        return [], [{"rule": "paid_fallback_for_free_route"}]
    return normalized, []


def configured_routes() -> list[dict[str, str]]:
    return route_configuration()[0]


def route_diagnostics() -> dict:
    routes, errors = route_configuration()
    _, document_format, _ = parse_route_document(setting("LLM_ROUTES_JSON")) if setting("LLM_ROUTES_JSON") else (None, "absent", [])
    return {"configured": bool(routes), "route_count": len(routes), "validation_errors": errors,
            "document_format": document_format,
            "policy": "free_only" if free_only_routes(routes) else "budgeted" if routes else "unavailable"}



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
