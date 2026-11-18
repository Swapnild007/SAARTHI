import hashlib

import httpx
import pytest

from backend import app as runtime
from backend import onboarding
from backend.passwords import valid_hash
from backend.private_session import COOKIE
from backend.tests.test_http_contract import deployment


@pytest.fixture
def mobile(deployment, monkeypatch):
    client, turns, calls = deployment
    monkeypatch.delenv("SAARTHI_OWNER_PASSWORD", raising=False)
    monkeypatch.delenv("SAARTHI_OWNER_PASSWORD_HASH", raising=False)
    monkeypatch.setenv("SAARTHI_OWNER_AUTH_STORE", "database")
    state = {"credential": None, "grant": None, "expired": False}

    async def credential(owner):
        assert owner == "owner-a"
        return state["credential"]

    async def limited(owner):
        return True

    async def management(token):
        return token == "authorized-management-fixture"

    async def issue(owner, digest, intent, legacy):
        if intent == "setup" and state["credential"]:
            return False
        state["grant"] = digest
        return True

    async def complete(owner, digest, encoded, legacy):
        if state["expired"] or state["grant"] != digest:
            return False
        assert valid_hash(encoded)
        state.update(credential=encoded, grant=None)
        return True

    monkeypatch.setattr(runtime.store, "owner_password", credential)
    monkeypatch.setattr(runtime.store, "claim_login", limited)
    monkeypatch.setattr(runtime.store, "issue_owner_grant", issue)
    monkeypatch.setattr(runtime.store, "complete_owner_setup", complete)
    monkeypatch.setattr(runtime, "verify_deployment_access", management)
    return client, state, turns, calls


def verify(client, intent="setup"):
    response = client.post("/api/onboarding/verify", json={
        "management_token": "authorized-management-fixture", "intent": intent,
    })
    assert response.status_code == 200, response.text
    assert response.json() == {"ok": True, "expires_in_seconds": 600}
    assert "HttpOnly" in response.headers["set-cookie"]


def test_first_setup_is_management_authorized_and_one_time(mobile):
    client, state, _, calls = mobile
    assert client.get("/api/onboarding").json()["stage"] == "verify_owner"
    assert client.get("/api/health").json()["owner_configured"] is False
    assert client.post("/api/onboarding/password", json={"password": "my-owner-password-long-enough"}).status_code == 403
    denied = client.post("/api/onboarding/verify", json={"management_token": "invalid"})
    assert denied.status_code == 403 and state["grant"] is None
    verify(client)
    cookie = client.cookies.get(onboarding.GRANT_COOKIE)
    assert state["grant"] == onboarding.authorization_digest("local", "http://127.0.0.1:8000", cookie)
    assert cookie not in client.post("/api/onboarding/verify", json={"management_token": "invalid"}).text
    saved = client.post("/api/onboarding/password", json={"password": "my-owner-password-long-enough"})
    assert saved.status_code == 200
    assert client.get("/api/session").json()["authenticated"] is True
    assert client.get("/api/health").json()["owner_configured"] is True
    assert client.get("/").status_code == 200
    assert client.get("/api/session").status_code == 200
    assert client.post("/api/command", json={"message": "First authenticated fixture turn"}).json()["ok"]
    assert len(calls) == 1
    # Direct replay of the consumed authorization cannot change the password.
    client.cookies.set(onboarding.GRANT_COOKIE, cookie, path="/api/onboarding")
    assert client.post("/api/onboarding/password", json={"password": "different-password-long-enough"}).status_code == 403
    assert client.post("/api/onboarding/verify", json={
        "management_token": "authorized-management-fixture",
    }).status_code == 409


def test_recovery_rotates_sessions_and_keeps_conversations(mobile):
    client, state, turns, _ = mobile
    verify(client)
    assert client.post("/api/onboarding/password", json={"password": "initial-password-long-enough"}).status_code == 200
    client.post("/api/command", json={"message": "Preserved", "conversation_id": "saved-thread"})
    original_token = client.cookies.get(COOKIE)
    verify(client, "recover")
    assert client.post("/api/onboarding/password", json={"password": "replacement-password-long-enough"}).status_code == 200
    new_token = client.cookies.get(COOKIE)
    assert original_token != new_token and len(turns) == 1
    from dataclasses import replace
    from backend.private_session import Scope
    scope = replace(Scope.read(), password=state["credential"])
    assert not scope.authenticated(original_token)
    assert scope.authenticated(new_token)
    client.post("/api/session/logout")
    assert client.get("/api/session").status_code == 401
    assert client.post("/api/session/login", json={"password": "initial-password-long-enough"}).status_code == 401
    assert client.post("/api/session/login", json={"password": "replacement-password-long-enough"}).status_code == 200


def test_expiry_csrf_and_missing_store_fail_safely(mobile, monkeypatch):
    client, state, _, _ = mobile
    assert client.post("/api/onboarding/verify", json={"management_token": "authorized-management-fixture"},
                       headers={"Origin": "https://attacker.invalid"}).status_code == 403
    verify(client)
    state["expired"] = True
    assert client.post("/api/onboarding/password", json={"password": "my-owner-password-long-enough"}).status_code == 403
    assert state["credential"] is None

    async def missing(owner):
        raise RuntimeError("private database secret must not leak")

    monkeypatch.setattr(runtime.store, "owner_password", missing)
    assert client.get("/api/onboarding").json()["stage"] == "connection_required"
    response = client.post("/api/onboarding/verify", json={"management_token": "authorized-management-fixture"})
    assert response.status_code == 503 and "secret" not in response.text


def test_management_verification_proves_preview_write_permission(monkeypatch):
    import asyncio
    monkeypatch.setenv("SAARTHI_ENV", "local")
    monkeypatch.setenv("SAARTHI_DEPLOYMENT_PROJECT_ID", "prj_fixture")
    monkeypatch.setenv("SAARTHI_DEPLOYMENT_TEAM_ID", "team_fixture")
    requests = []

    def handle(request):
        requests.append(request)
        assert request.url.host == "api.vercel.com"
        assert request.headers["Authorization"] == "Bearer temporary-fixture"
        if request.method == "POST":
            import json
            payload = json.loads(request.content)
            assert payload["target"] == ["preview"]
            assert payload["gitBranch"] == onboarding.BRANCH
            return httpx.Response(200, json={"created": [{"id": "env_fixture"}]})
        assert request.method == "DELETE" and request.url.path.endswith("/env_fixture")
        return httpx.Response(204)

    real_client = httpx.AsyncClient
    monkeypatch.setattr(onboarding.httpx, "AsyncClient",
                        lambda **options: real_client(transport=httpx.MockTransport(handle), **options))
    assert asyncio.run(onboarding.verify_deployment_access("temporary-fixture"))
    assert len(requests) == 2


def test_setup_authorization_is_bound_to_environment_and_origin():
    first = onboarding.authorization_digest("preview", "https://one.vercel.app", "token")
    assert first != onboarding.authorization_digest("preview", "https://two.vercel.app", "token")
    assert first != onboarding.authorization_digest("production", "https://one.vercel.app", "token")
