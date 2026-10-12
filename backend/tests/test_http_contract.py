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
    assert "fallbackSend" not in boot_js
    assert "/api/command" not in boot_js
    assert "eeldalviz-1192.vercel.app" not in runtime
    assert "https://saarthi-swapneeldalvi3-1192.vercel.app" in runtime

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

