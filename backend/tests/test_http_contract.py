from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import app


ROOT = Path(__file__).resolve().parents[2]


def _fake_result(message: str, assistant: str):
    return {
        "ok": True,
        "reply": f"Echo: {message}",
        "run_id": "smoke-run",
        "intent": {"name": "chat"},
        "provider": "test",
        "assistant": assistant,
    }


def test_command_plain_cross_origin_contract(monkeypatch):
    monkeypatch.setattr(
        "backend.app.engine.run",
        lambda **kwargs: _fake_result(kwargs["message"], kwargs["assistant"]),
    )
    client = TestClient(app)
    payload = {
        "message": "Hello Saarthi",
        "mode": "chat",
        "assistant": "saarthi",
        "context": {},
    }
    response = client.post(
        "/api/command/plain",
        content='{"message":"Hello Saarthi","mode":"chat","assistant":"saarthi","context":{}}',
        headers={"Content-Type": "text/plain", "Origin": "https://swapnild007.github.io"},
    )
    assert response.status_code == 200
    assert response.json()["reply"] == "Echo: Hello Saarthi"
    assert response.headers["access-control-allow-origin"] == "https://swapnild007.github.io"


def test_command_json_contract(monkeypatch):
    monkeypatch.setattr(
        "backend.app.engine.run",
        lambda **kwargs: _fake_result(kwargs["message"], kwargs["assistant"]),
    )
    client = TestClient(app)
    response = client.post(
        "/api/command",
        json={
            "message": "Hello Saarthi",
            "mode": "chat",
            "assistant": "saarthi",
            "context": {},
        },
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_command_plain_rejects_invalid_payload():
    client = TestClient(app)
    response = client.post(
        "/api/command/plain",
        content="not-json",
        headers={"Content-Type": "text/plain"},
    )
    assert response.status_code == 400


def test_frontend_composer_contract():
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    app_js = (ROOT / "scripts" / "app.js").read_text(encoding="utf-8")
    boot_js = (ROOT / "scripts" / "boot.js").read_text(encoding="utf-8")
    runtime = (ROOT / "config" / "runtime.json").read_text(encoding="utf-8")

    assert '<form class="command conversation-composer" id="conversationComposer"' in index
    assert 'id="sendCommand"' in index
    assert "type=\"submit\"" in index
    assert "composerForm?.addEventListener('submit'" in app_js
    assert "sendInFlight" in app_js
    assert "/api/command/plain" in app_js
    assert "if(window.SaarthiApp?.submit) return;" in boot_js
    assert "eeldalviz-1192.vercel.app" not in runtime
    assert "https://saarthi-nine-chi.vercel.app" in runtime

def test_command_plain_has_runtime_deadline(monkeypatch):
    import asyncio
    from backend import app as app_module

    async def fake_wait_for(awaitable, timeout):
        if hasattr(awaitable, "close"):
            awaitable.close()
        raise asyncio.TimeoutError

    monkeypatch.setattr(app_module.asyncio, "wait_for", fake_wait_for)
    client = TestClient(app_module.app)
    response = client.post(
        "/api/command/plain",
        content='{"message":"Hello Saarthi","mode":"chat","assistant":"saarthi","context":{}}',
        headers={"Content-Type": "text/plain"},
    )
    assert response.status_code == 200
    assert response.json()["execution"] == "timed-out-safely"
