import json
from uuid import uuid4

import pytest

from backend import app as runtime, deployment, execution
from backend.engine import OpenAICompatibleProvider
from backend.tests.test_http_contract import deployment as private_deployment, login


def configure(monkeypatch, routes):
    monkeypatch.setenv("SAARTHI_ENV", "preview")
    monkeypatch.setenv("SAARTHI_PREVIEW_LLM_ROUTES_JSON", json.dumps(routes))


def route(model="openrouter/free"):
    return {"url": "https://openrouter.ai/api/v1", "key": "fixture-key", "model": model}


@pytest.mark.parametrize(("value", "rule", "field"), [
    ("{broken", "invalid_json", None),
    ("[]", "route_count_or_type", None),
    ('[{"url":"https://openrouter.ai/api/v1","model":"openrouter/free"}]', "missing_or_invalid_field", "key"),
    (json.dumps([dict(route(), url="https://other.invalid/v1")]), "endpoint_not_allowed", "url"),
    (json.dumps([dict(route(), model="openrouter/free?paid=1")]), "invalid_model_identifier", "model"),
    (json.dumps([dict(route(), models=["vendor/paid"])]), "unsupported_route_fields", None),
])
def test_configuration_diagnostics_are_exact_and_redacted(monkeypatch, value, rule, field):
    monkeypatch.setenv("SAARTHI_ENV", "preview")
    monkeypatch.setenv("SAARTHI_PREVIEW_LLM_ROUTES_JSON", value)
    report = deployment.route_diagnostics()
    assert not report["configured"]
    failure = report["validation_errors"][0]
    assert failure["rule"] == rule
    if field:
        assert failure["field"] == field
    assert "fixture-key" not in str(report)
    assert "other.invalid" not in str(report)


def test_free_configuration_is_valid_without_paid_settings(monkeypatch):
    configure(monkeypatch, route())
    assert deployment.route_diagnostics() == {
        "configured": True, "route_count": 1, "validation_errors": [], "policy": "free_only", "document_format": "json",
    }
    assert deployment.free_only_routes(deployment.configured_routes())
    assert deployment.SpendLimits.read() is None
    assert deployment.configured_routes()[0]["name"] == "route-1"


def test_free_only_cannot_fallback_to_paid(monkeypatch):
    configure(monkeypatch, [dict(route(), name="free"), dict(route("vendor/paid"), name="paid")])
    assert deployment.configured_routes() == []
    assert deployment.route_diagnostics()["validation_errors"] == [{"rule": "paid_fallback_for_free_route"}]


@pytest.mark.parametrize(("body", "accepted"), [
    ({"model": "vendor/model:free", "choices": [{"message": {"content": "Actual text"}}], "usage": {"cost": 0}}, True),
    ({"choices": [], "usage": {"cost": 0}}, False),
    ({"choices": [{"message": {"content": "Actual text"}}], "usage": {"cost": 1}}, False),
    ({"choices": [{"message": {"content": "Actual text"}}], "usage": {"cost": "NaN"}}, False),
    ({"error": {"message": "private detail"}, "choices": [{"message": {"content": "text"}}]}, False),
])
def test_free_request_disallows_paid_routing_and_checks_response(monkeypatch, body, accepted):
    configure(monkeypatch, [route()])
    captured = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self, size):
            return json.dumps(body).encode()

    class Opener:
        def open(self, request, timeout):
            assert request.full_url == "https://openrouter.ai/api/v1/chat/completions"
            captured.append(json.loads(request.data))
            return Response()

    monkeypatch.setattr("backend.engine.build_opener", lambda *_: Opener())
    token = execution.timings.set({})
    try:
        provider = OpenAICompatibleProvider()
        assert provider.request_timeout == 14
        args = dict(message="A short question", system="Answer briefly", context={}, assistant="saarthi")
        if accepted:
            assert provider._request(provider.routes[0], **args)[0] == "Actual text"
            assert provider.last_model == "vendor/model:free"
        else:
            with pytest.raises(ValueError):
                provider._request(provider.routes[0], **args)
    finally:
        execution.timings.reset(token)
    assert captured[0]["model"] == "openrouter/free"
    assert captured[0]["provider"] == {"max_price": {"prompt": 0, "completion": 0}, "allow_fallbacks": False}
    assert not {"models", "plugins", "tools"} & captured[0].keys()


def test_free_chat_retains_auth_persistence_and_retry(private_deployment, monkeypatch):
    client, turns, calls = private_deployment
    payload = {"message": "Free fixture question", "conversation_id": "free-thread", "turn_id": str(uuid4())}
    assert client.post("/api/command", json=payload).status_code == 401
    login(client)
    monkeypatch.setenv("SAARTHI_LLM_ROUTES_JSON", json.dumps([route()]))
    monkeypatch.setattr(runtime.engine, "cloud", OpenAICompatibleProvider())
    monkeypatch.setattr(runtime, "hosted", lambda: True)

    async def never_admit_paid(*args):
        raise AssertionError("A free request must not require paid reservation")

    monkeypatch.setattr(runtime.store, "admit_turn", never_admit_paid)
    first = client.post("/api/command", json=payload).json()
    assert first["ok"]
    assert client.post("/api/command", json=payload).json() == first
    assert len(turns) == len(calls) == 1
    assert next(iter(turns.values()))["state"] == "completed"


@pytest.mark.parametrize(("wrap", "format_name"), [
    (lambda value: "SAARTHI_PREVIEW_LLM_ROUTES_JSON='" + value + "'", "quoted_json"),
    (lambda value: chr(96)*3 + "json\n" + value + "\n" + chr(96)*3, "fenced_json"),
    (lambda value: json.dumps(value), "encoded_json"),
])
def test_copy_paste_wrappers_still_require_validated_inner_json(monkeypatch, wrap, format_name):
    monkeypatch.setenv("SAARTHI_ENV", "preview")
    monkeypatch.setenv("SAARTHI_PREVIEW_LLM_ROUTES_JSON", wrap(json.dumps([route()])))
    report = deployment.route_diagnostics()
    assert report["configured"] and report["document_format"] == format_name
    monkeypatch.setenv("SAARTHI_PREVIEW_LLM_ROUTES_JSON", wrap("{broken"))
    assert deployment.route_diagnostics()["validation_errors"][0]["rule"] == "invalid_json"


def test_complete_key_only_is_restricted_to_the_free_router(monkeypatch):
    monkeypatch.setenv("SAARTHI_ENV", "preview")
    monkeypatch.setenv("SAARTHI_PREVIEW_LLM_ROUTES_JSON", "sk-or-v1-" + "a" * 64)
    routes = deployment.configured_routes()
    assert routes[0]["model"] == "openrouter/free" and deployment.free_only_routes(routes)
    assert deployment.route_diagnostics()["document_format"] == "free_key_only"
    monkeypatch.setenv("SAARTHI_PREVIEW_LLM_ROUTES_JSON", '{"key":"sk-or-v1-' + 'a' * 64)
    assert deployment.configured_routes() == []


def test_invalid_provider_logging_is_redacted(private_deployment, monkeypatch, caplog):
    client, turns, calls = private_deployment
    login(client)
    monkeypatch.setenv("SAARTHI_LLM_ROUTES_JSON", '{"key":"private-secret-that-must-not-leak"')
    monkeypatch.setattr(runtime.engine, "cloud", OpenAICompatibleProvider())
    monkeypatch.setattr(runtime, "hosted", lambda: True)
    result = client.post("/api/command", json={"message": "Do not execute"}).json()
    assert result["error_code"] == "provider_unconfigured"
    assert result["configuration"]["validation_errors"][0]["rule"] == "invalid_json"
    assert "private-secret" not in str(result) + caplog.text
    assert not turns and not calls
