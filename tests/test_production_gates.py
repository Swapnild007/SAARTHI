import json

import httpx
import pytest
from fastapi.testclient import TestClient

from backend import app as runtime
from backend import deployment
from backend.engine import OpenAICompatibleProvider
from scripts.candidate_smoke import approved_origin, login, send


def test_preview_uses_only_scoped_credentials_and_pinned_database(monkeypatch):
    monkeypatch.setenv("VERCEL_ENV", "preview")
    monkeypatch.setenv("SAARTHI_ENV", "preview")
    monkeypatch.setenv("SAARTHI_LLM_API_KEY", "global-fixture")
    monkeypatch.setenv("SAARTHI_PRODUCTION_SUPABASE_URL", "https://production.invalid")
    assert deployment.configured_routes() == []
    assert deployment.storage_endpoint() == ("", "")
    project = "a" * 20
    monkeypatch.setenv("SAARTHI_PREVIEW_SUPABASE_PROJECT_REF", project)
    monkeypatch.setenv("SAARTHI_PREVIEW_SUPABASE_URL", "https://production.invalid")
    monkeypatch.setenv("SAARTHI_PREVIEW_SUPABASE_SERVICE_ROLE_KEY", "preview-fixture")
    assert deployment.storage_endpoint() == ("", "")
    monkeypatch.setenv("SAARTHI_PREVIEW_SUPABASE_URL", f"https://{project}.supabase.co")
    assert deployment.storage_endpoint() == (f"https://{project}.supabase.co", "preview-fixture")
    monkeypatch.setenv("SAARTHI_PREVIEW_LLM_ROUTES_JSON", json.dumps([
        {"name": "preview", "url": "https://openrouter.ai/api/v1", "key": "fixture", "model": "model"},
    ]))
    assert deployment.configured_routes()[0]["name"] == "preview"
    monkeypatch.setenv("SAARTHI_PREVIEW_LLM_ROUTES_JSON", "{broken")
    assert deployment.configured_routes() == []


def test_paid_admission_requires_verified_configuration(monkeypatch):
    monkeypatch.setenv("SAARTHI_ENV", "staging")
    for name, value in {"LLM_TURN_RESERVE_MICRO_USD": "25", "DAILY_BUDGET_MICRO_USD": "50",
                        "MONTHLY_BUDGET_MICRO_USD": "100"}.items():
        monkeypatch.setenv("SAARTHI_STAGING_" + name, value)
    assert deployment.SpendLimits.read() is None
    monkeypatch.setenv("SAARTHI_STAGING_LLM_HARD_CAP_CONFIRMED", "true")
    assert deployment.SpendLimits.read() == deployment.SpendLimits(25, 50, 100)
    assert deployment.SpendLimits.read("HERMES") is None


@pytest.mark.parametrize(("data", "allowed"), [
    ({"limit": 0.01, "limit_remaining": 0.005}, True),
    ({"limit": None, "limit_remaining": None}, False),
    ({"limit": 1, "limit_remaining": 0.1}, False),
    ({"limit": 0.01, "limit_remaining": 0}, False),
    ({"limit": 0.01, "limit_remaining": 0.005, "limit_reset": "daily"}, False),
])
def test_verify_upstream_key_ceiling(data, allowed):
    assert deployment.upstream_key_ceiling(data, 10_000) is allowed


@pytest.mark.parametrize("capped", [False, True])
def test_hosted_adapter_checks_key_before_completion(monkeypatch, capped):
    from backend import execution
    monkeypatch.setenv("SAARTHI_ENV", "preview")
    for name, value in {
        "LLM_ROUTES_JSON": '[{"name":"preview","url":"https://openrouter.ai/api/v1","key":"fixture","model":"model"}]',
        "LLM_TURN_RESERVE_MICRO_USD": "20", "DAILY_BUDGET_MICRO_USD": "10000",
        "MONTHLY_BUDGET_MICRO_USD": "10000", "LLM_HARD_CAP_CONFIRMED": "true",
    }.items():
        monkeypatch.setenv("SAARTHI_PREVIEW_" + name, value)
    paths = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self, _size):
            if paths[-1].endswith("/key"):
                bound = 0.005 if capped else None
                return json.dumps({"data": {"limit": bound, "limit_remaining": bound}}).encode()
            return b'{"choices":[{"message":{"content":"upstream answer"}}],"usage":{"cost":0.000002}}'

    class Opener:
        def open(self, request, timeout):
            paths.append(request.full_url)
            return Response()

    monkeypatch.setattr("backend.engine.build_opener", lambda *_: Opener())
    token = execution.timings.set({})
    try:
        provider = OpenAICompatibleProvider()
        def request():
            return provider._request(provider.routes[0], message="hello", system="be helpful",
                                     context={}, assistant="saarthi")

        if capped:
            assert request() == ("upstream answer", {"cost": 0.000002})
        else:
            with pytest.raises(ValueError, match="key budget"):
                request()
    finally:
        execution.timings.reset(token)
    assert paths == ["https://openrouter.ai/api/v1/key"] + (
        ["https://openrouter.ai/api/v1/chat/completions"] if capped else []
    )


def test_cost_is_rounded_up_and_invalid_usage_is_ignored():
    assert runtime.reported_cost({"cost": "0.0000001"}) == 1
    assert runtime.reported_cost({"cost": "NaN"}) is None
    assert runtime.reported_cost({"cost": -1}) is None
    assert runtime.reported_cost({"prompt_tokens": 100}) is None


def test_unconfigured_preview_reports_build_and_denies_private_routes(monkeypatch):
    monkeypatch.setenv("VERCEL_ENV", "preview")
    monkeypatch.setenv("VERCEL_GIT_COMMIT_SHA", "a" * 40)
    monkeypatch.delenv("SAARTHI_ENV", raising=False)
    with TestClient(runtime.app) as client:
        health = client.get("/api/health").json()
        assert (health["ok"], health["environment"], health["commit"]) == (False, "preview", "a" * 40)
        assert client.get("/api/conversations").status_code == 503


def test_smoke_refuses_wrong_origin_or_sha_before_credentials():
    with pytest.raises(ValueError):
        approved_origin("https://preview.invalid", "https://staging.invalid")
    with pytest.raises(ValueError):
        approved_origin("https://preview.invalid/?redirect=test", "https://preview.invalid/?redirect=test")
    requests = []

    def handler(request):
        requests.append(request.url.path)
        return httpx.Response(200, json={"ok": True, "environment": "staging", "commit": "a" * 40})

    with httpx.Client(base_url="https://staging.invalid", transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(RuntimeError, match="SHA mismatch"):
            login(client, "staging", "b" * 40, "fixture")
    assert requests == ["/api/health"]


def test_candidate_smoke_requires_upstream_response_source():
    payload = {"turn_id": "turn", "conversation_id": "thread"}
    reply = dict(payload, ok=True, execution="completed", provider="ai-gateway", reply="example")
    with httpx.Client(base_url="https://staging.invalid", transport=httpx.MockTransport(
        lambda _: httpx.Response(200, json=reply)
    )) as client:
        reply["response_source"] = "local_visualization"
        with pytest.raises(RuntimeError, match="Upstream"):
            send(client, payload, "ai-gateway")
        reply["response_source"] = "upstream"
        assert send(client, payload, "ai-gateway") == reply


@pytest.mark.parametrize(("upstream", "code"), [
    (httpx.Response(401), "hermes_unavailable"),
    (httpx.Response(429), "provider_rate_limited"),
    (httpx.Response(200, json={"choices": [{"message": {"content": "text", "tool_calls": [{}]}}]}),
     "hermes_tool_response"),
    (httpx.ReadTimeout("private detail"), "provider_timeout"),
])
def test_hermes_gateway_failures_are_typed_without_tools(monkeypatch, upstream, code):
    import asyncio
    from backend import hermes_bridge
    from backend.private_session import Scope
    monkeypatch.setattr(hermes_bridge, "configuration", lambda _: ("https://gateway.invalid", "server-secret"))
    client = httpx.AsyncClient

    def gateway(request):
        assert request.headers["Authorization"] == "Bearer server-secret"
        assert "tools" not in json.loads(request.content)
        if isinstance(upstream, Exception):
            raise upstream
        return upstream

    monkeypatch.setattr(hermes_bridge.httpx, "AsyncClient",
                        lambda **options: client(transport=httpx.MockTransport(gateway), **options))
    scope = Scope("staging", "https://stage.invalid", "a" * 40, "owner", "password", "key", 10)
    result = asyncio.run(hermes_bridge.generate(scope, "thread", "test", []))
    assert result["error_code"] == code
    assert result["verification"]["verified"] is False
    assert "private detail" not in str(result)


def test_storage_transmits_only_owner_scoped_filters_and_rejects_wrong_marker(monkeypatch):
    import asyncio
    from backend.storage import CloudStore
    monkeypatch.setenv("SAARTHI_SUPABASE_URL", "https://storage.invalid")
    monkeypatch.setenv("SAARTHI_SUPABASE_SERVICE_ROLE_KEY", "fixture-role")
    requests = []

    def gateway(request):
        requests.append(request)
        assert request.headers["Authorization"] == "Bearer fixture-role"
        if request.url.path.endswith("/saarthi_scope"):
            return httpx.Response(200, json=[{"environment": "production"}])
        return httpx.Response(200, json=[])

    client = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient",
                        lambda **options: client(transport=httpx.MockTransport(gateway), **options))
    store = CloudStore()
    with pytest.raises(RuntimeError, match="another environment"):
        asyncio.run(store.check_scope("preview"))
    assert len(requests) == 1
    assert asyncio.run(store.recovery_turns("owner-a", "thread", 12, 5)) == []
    assert requests[-1].url.params["owner"] == "eq.owner-a"
    assert requests[-1].url.params["seq"] == "gt.12"
    assert requests[-1].url.params["limit"] == "5"
