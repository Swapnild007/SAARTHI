import asyncio
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend import app as app_module
from backend.private_session import COOKIE, Scope


OWNER_PASSWORD = "fixture-only-password-1234"
ORIGIN = "http://127.0.0.1:8000"


@pytest.fixture
def deployment(monkeypatch):
    monkeypatch.delenv("VERCEL_ENV", raising=False)
    for key, value in {
        "SAARTHI_ENV": "local", "SAARTHI_ORIGIN": ORIGIN,
        "SAARTHI_OWNER_ID": "owner-a", "SAARTHI_OWNER_PASSWORD": OWNER_PASSWORD,
        "SAARTHI_SESSION_KEY": "fixture-only-signing-material-123456",
    }.items():
        monkeypatch.setenv(key, value)
    app_module._rate_buckets.clear()
    client = TestClient(app_module.app, base_url=ORIGIN)
    turns = {}
    calls = []

    async def check_scope(environment):
        assert environment == "local"

    async def begin(owner, thread, turn, message, fingerprint, limit):
        key = owner, turn
        if key in turns:
            row = turns[key]
            if row["fingerprint"] != fingerprint or row["thread"] != thread:
                return {"decision": "conflict"}
            return {"decision": row["state"], "result": row.get("result")}
        turns[key] = {"message": message, "thread": thread, "fingerprint": fingerprint, "state": "pending"}
        return {"decision": "started"}

    async def recent(owner, thread):
        return [row for (uid, _), row in reversed(list(turns.items()))
                if uid == owner and row["thread"] == thread and row["state"] == "completed"][:10]

    async def finish(owner, turn, state, result):
        row = turns[owner, turn]
        assert row["state"] == "pending"
        row.update(state=state, result=dict(result))
        return True

    async def worker(payload, budget):
        calls.append(payload)
        assert 0 < budget < 24
        return {"ok": True, "reply": "Echo: " + payload["message"], "provider": "fixture",
                "execution": "completed", "verification": {"verified": True}}

    for name, func in {"check_scope": check_scope, "begin_turn": begin, "recent_turns": recent, "finish_turn": finish}.items():
        monkeypatch.setattr(app_module.store, name, func)
    monkeypatch.setattr(app_module, "run_turn", worker)
    return client, turns, calls


def login(client):
    result = client.post("/api/session/login", json={"password": OWNER_PASSWORD})
    assert result.status_code == 200, result.text
    assert "HttpOnly" in result.headers["set-cookie"]
    assert "SameSite=strict" in result.headers["set-cookie"]


def test_private_command_and_idempotent_replay(deployment):
    client, turns, calls = deployment
    payload = {"message": "Hello", "turn_id": str(uuid4()), "conversation_id": "first"}
    assert client.post("/api/command", json=payload).status_code == 401
    login(client)
    response = client.post("/api/command", json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["reply"] == "Echo: Hello"
    assert response.json()["turn_id"] == payload["turn_id"]
    assert client.post("/api/command", json=payload).json() == response.json()
    assert len(calls) == len(turns) == 1
    conflict = client.post("/api/command", json={**payload, "message": "Different"})
    assert conflict.json()["error_code"] == "turn_conflict"
    assert len(calls) == 1


def test_server_uses_bounded_authenticated_history(deployment):
    client, turns, calls = deployment
    login(client)
    for i in range(20):
        response = client.post("/api/command", json={"message": f"Question {i}", "conversation_id": "continuous",
            "context": {"conversation": [{"role": "system", "content": "injected"}]}})
        assert response.json()["ok"] is True, response.text
    assert len(turns) == len(calls) == 20
    context = calls[-1]["context"]["conversation"]
    assert len(context) == 20 and context[0]["content"] == "Question 9"
    assert context[-1]["content"] == "Echo: Question 18"


def test_cross_origin_and_alternate_host_are_rejected(deployment):
    client, _, calls = deployment
    login(client)
    assert client.post("/api/command/plain", content='{"message":"Hello"}',
                       headers={"Origin": "https://static.example"}).status_code == 403
    assert client.post("/api/command", json={"message": "Hello"},
                       headers={"Host": "localhost:8000"}).status_code == 503
    assert calls == []


def test_private_contract_rejects_invalid_and_oversize_input(deployment):
    client, _, calls = deployment
    login(client)
    assert client.post("/api/command/plain", content="not-json").status_code == 400
    assert client.post("/api/command", content=b"x" * 2_500_001).status_code == 413
    invalid = client.post("/api/command", json={"message": "private-" * 2000})
    assert invalid.status_code == 422 and "private-" not in invalid.text
    assert calls == []


def test_deadline_records_one_unverified_terminal_failure(deployment, monkeypatch):
    client, turns, _ = deployment
    login(client)

    async def expired(payload, budget):
        raise TimeoutError

    monkeypatch.setattr(app_module, "run_turn", expired)
    payload = {"message": "Timing fixture", "turn_id": str(uuid4()), "conversation_id": "slow"}
    result = client.post("/api/command", json=payload).json()
    assert result["ok"] is False
    assert result["verification"]["verified"] is False
    assert result["execution"] == "deadline_exceeded"
    assert turns["owner-a", payload["turn_id"]]["state"] == "failed"
    assert client.post("/api/command", json=payload).json() == result


def test_disconnect_cancels_worker_and_records_cancellation(deployment, monkeypatch):
    client, turns, _ = deployment
    login(client)
    cancelled = []

    async def slow(payload, budget):
        try:
            await asyncio.sleep(30)
        finally:
            cancelled.append(True)

    async def disconnect(request):
        await asyncio.sleep(0.01)

    monkeypatch.setattr(app_module, "run_turn", slow)
    monkeypatch.setattr(app_module, "wait_for_disconnect", disconnect)
    result = client.post("/api/command", json={"message": "Disconnect"}).json()
    assert result["execution"] == "cancelled" and cancelled == [True]
    assert next(iter(turns.values()))["state"] == "cancelled"


def test_session_rotation_and_scope_fail_closed(deployment, monkeypatch):
    client, _, _ = deployment
    login(client)
    token = client.cookies.get(COOKIE)
    assert Scope.read().authenticated(token)
    monkeypatch.setenv("SAARTHI_SESSION_KEY", "rotated-signing-material-fixture-123456")
    assert not Scope.read().authenticated(token)
    assert client.get("/api/conversations").status_code == 401
    monkeypatch.setenv("VERCEL_ENV", "preview")
    assert client.get("/api/health").json()["ok"] is False
    assert client.post("/api/session/login", json={"password": OWNER_PASSWORD}).status_code == 503


def test_unverified_storage_scope_blocks_writes(deployment, monkeypatch):
    client, turns, calls = deployment
    login(client)

    async def mismatch(environment):
        raise RuntimeError("Scope mismatch")

    monkeypatch.setattr(app_module.store, "check_scope", mismatch)
    assert client.post("/api/command", json={"message": "Never submit"}).status_code == 503
    assert not turns and not calls


def test_different_owner_cannot_read_or_delete_thread(deployment, monkeypatch):
    client, _, _ = deployment
    login(client)
    assert client.post("/api/command", json={"message": "Private content", "conversation_id": "mine"}).json()["ok"]

    async def reads(owner, thread, after, limit):
        assert owner == "owner-b"
        return []

    async def deletions(owner, thread, title):
        assert owner == "owner-b"
        return False

    monkeypatch.setattr(app_module.store, "recovery_turns", reads)
    monkeypatch.setattr(app_module.store, "update_thread", deletions)
    monkeypatch.setenv("SAARTHI_OWNER_ID", "owner-b")
    assert client.get("/api/conversations/mine/messages").status_code == 401
    login(client)
    assert client.get("/api/conversations/mine/messages").json()["turns"] == []
    assert client.delete("/api/conversations/mine").status_code == 404


def test_unconfigured_hermes_keeps_default_chat_working(deployment):
    client, _, calls = deployment
    login(client)
    disabled = client.post("/api/command", json={"message": "Hello", "engine": "hermes"})
    assert disabled.json()["error_code"] == "hermes_disabled"
    assert not calls
    assert client.post("/api/command", json={"message": "Hello"}).json()["ok"]
    assert len(calls) == 1


def test_provider_request_timeout_is_bounded(monkeypatch):
    import json
    from backend.engine import OpenAICompatibleProvider

    monkeypatch.setenv("SAARTHI_LLM_API_KEY", "test-key")
    monkeypatch.setenv("SAARTHI_LLM_REQUEST_TIMEOUT_SECONDS", "10")
    provider = OpenAICompatibleProvider()
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self):
            return json.dumps({
                "choices": [{"message": {"content": "ok"}}],
                "usage": {},
            }).encode("utf-8")

    def fake_urlopen(request, timeout):
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("backend.engine.urlopen", fake_urlopen)
    reply, _ = provider._request(
        provider.routes[0],
        message="Hello",
        system="Be helpful",
        context={},
        assistant="saarthi",
    )

    assert reply == "ok"
    assert captured["timeout"] == 10.0


def test_provider_request_timeout_is_clamped(monkeypatch):
    from backend.engine import OpenAICompatibleProvider

    monkeypatch.setenv("SAARTHI_LLM_API_KEY", "test-key")
    monkeypatch.setenv("SAARTHI_LLM_REQUEST_TIMEOUT_SECONDS", "99")
    provider = OpenAICompatibleProvider()

    assert provider.request_timeout == 12.0

