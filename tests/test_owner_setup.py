import time

import httpx
import pytest

from backend.passwords import hash_password, verify_password
from backend.private_session import Scope, COOKIE
from backend.tests.test_http_contract import deployment, login, OWNER_PASSWORD
from scripts.setup_owner import configure


def test_hash_and_expiration(monkeypatch):
    password = "owner-chosen-long-passphrase"
    encoded = hash_password(password)
    assert password not in encoded
    assert verify_password(password, encoded)
    assert not verify_password("wrong", encoded)
    scope = Scope("local", "http://localhost", "", "owner", encoded, "key", 10)
    token = scope.issue()
    assert scope.authenticated(token)
    monkeypatch.setattr(time, "time", lambda: 10**12)
    assert not scope.authenticated(token)


def test_hashed_login_reload_invalid_password_and_rotation(deployment, monkeypatch):
    client, _, _ = deployment
    monkeypatch.setenv("SAARTHI_OWNER_PASSWORD_HASH", hash_password(OWNER_PASSWORD))
    assert client.post("/api/session/login", json={"password": "incorrect"}).status_code == 401
    login(client)
    assert client.get("/").status_code == 200
    assert client.get("/api/session").json()["authenticated"]
    token = client.cookies.get(COOKIE)
    monkeypatch.setenv("SAARTHI_OWNER_PASSWORD_HASH", hash_password("replacement-password-long-enough"))
    assert client.get("/api/session").status_code == 401
    assert not Scope.read().authenticated(token)
    monkeypatch.setenv("SAARTHI_OWNER_PASSWORD_HASH", "malformed")
    assert client.get("/api/session").status_code == 503


def test_setup_requires_vercel_authorization_and_never_prints_secrets(capsys):
    requests = []

    def handle(request):
        requests.append(request)
        if request.method == "GET":
            return httpx.Response(200, json={"envs": []})
        payload = __import__("json").loads(request.content)
        assert payload["target"] == ["preview"]
        assert payload["gitBranch"] == "codex/saarthi-production-recovery"
        assert "owner-chosen-long-password" not in payload["value"]
        return httpx.Response(200, json={})

    with httpx.Client(base_url="https://api.vercel.com", transport=httpx.MockTransport(handle)) as client:
        configure(client, "project", "team", "codex/saarthi-production-recovery",
                  "owner", "owner-chosen-long-password")
    assert len(requests) == 5
    assert capsys.readouterr().out == ""
    with httpx.Client(base_url="https://api.vercel.com", transport=httpx.MockTransport(
        lambda _: httpx.Response(403)
    )) as client:
        with pytest.raises(RuntimeError, match="authorize"):
            configure(client, "project", "team", "branch", "owner", "owner-chosen-long-password")
