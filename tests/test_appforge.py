from fastapi.testclient import TestClient

from backend.app import app


def test_appforge_health_is_explicit_about_alpha_boundaries():
    response = TestClient(app).get("/api/appforge/health")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["feature"] == "appforge-alpha"
    assert body["production_deployments"] is False
    assert body["execution"] == "browser-preview-only"


def test_appforge_generate_requires_a_meaningful_prompt():
    response = TestClient(app).post("/api/appforge/generate", json={"prompt": "tiny", "project_name": "Test"})
    assert response.status_code == 422


def test_appforge_generate_returns_complete_safe_starter_when_model_has_no_html(monkeypatch):
    class FakeEngine:
        def run(self, **kwargs):
            return {"reply": "I can help with that.", "provider": "deterministic-fallback"}

    monkeypatch.setattr(app.state, "saarthi_engine", FakeEngine(), raising=False)
    response = TestClient(app).post(
        "/api/appforge/generate",
        json={"prompt": "Create a useful customer support dashboard", "project_name": "Support Desk"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["mode"] == "safe-starter"
    assert "provider" not in body
    assert "<!doctype html>" in body["html"].lower()
    assert "</html>" in body["html"].lower()
    assert "Support Desk" in body["html"]


def test_appforge_generate_uses_complete_html_from_coding_engine(monkeypatch):
    class FakeEngine:
        def run(self, **kwargs):
            return {
                "reply": "```html\n<!doctype html><html><head><title>Test</title></head><body><h1>Built</h1></body></html>\n```",
                "provider": "test-provider",
            }

    monkeypatch.setattr(app.state, "saarthi_engine", FakeEngine(), raising=False)
    response = TestClient(app).post(
        "/api/appforge/generate",
        json={"prompt": "Create a simple product dashboard", "project_name": "Test"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "ai-generated"
    assert "provider" not in body
    assert "<h1>Built</h1>" in body["html"]


def test_appforge_route_does_not_accept_unbounded_payloads():
    response = TestClient(app).post(
        "/api/appforge/generate",
        json={"prompt": "Build a dashboard " + ("x" * 5000), "project_name": "Test"},
    )
    assert response.status_code == 422


def test_appforge_workspace_route_serves_builder_html():
    response = TestClient(app).get("/appforge")
    assert response.status_code == 200
    assert "SAARTHI AppForge" in response.text
    assert 'src="/appforge/app.js"' in response.text
