import os
from unittest.mock import patch

from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)


def test_disabled_by_default():
    with patch.dict(os.environ, {"SAARTHI_HERMES_ENABLED": "false"}):
        assert client.get("/api/hermes/status").json()["enabled"] is False
        assert client.post("/api/hermes/chat", json={"message": "hello"}).status_code == 503


def test_authentication_and_response():
    env = {
        "SAARTHI_HERMES_ENABLED": "true",
        "SAARTHI_HERMES_URL": "http://127.0.0.1:8642",
        "SAARTHI_HERMES_API_KEY": "gateway-secret",
        "SAARTHI_HERMES_BRIDGE_KEY": "caller-secret",
    }
    with patch.dict(os.environ, env):
        assert client.post("/api/hermes/chat", json={"message": "hello"}).status_code == 401
        with patch("backend.hermes_bridge._request", return_value={"ok": True, "reply": "Hi", "provider": "hermes-agent", "conversation_id": "abc"}) as mock:
            response = client.post("/api/hermes/chat", headers={"Authorization": "Bearer caller-secret"}, json={"message": "hello", "conversation_id": "abc"})
            assert response.status_code == 200
            assert response.json()["reply"] == "Hi"
            mock.assert_called_once()


def test_reject_insecure_remote_gateway():
    with patch.dict(os.environ, {
        "SAARTHI_HERMES_ENABLED": "true",
        "SAARTHI_HERMES_URL": "http://example.org:8642",
        "SAARTHI_HERMES_API_KEY": "gateway-secret",
        "SAARTHI_HERMES_BRIDGE_KEY": "caller-secret",
    }):
        assert client.get("/api/hermes/status").json()["enabled"] is False
