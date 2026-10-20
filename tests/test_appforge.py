from fastapi.testclient import TestClient

from backend.app import app


def test_appforge_health_is_explicit_about_alpha_boundaries():
    response = TestClient(app).get("/api/appforge/health")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["feature"] == "appforge-alpha"
    assert body["production_deployments"] is False
    assert body["execution"] == "browser-preview-with-optional-isolated-build"
    assert isinstance(body["isolated_builds_configured"], bool)
    assert isinstance(body["project_backup_configured"], bool)


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



def test_appforge_build_is_disabled_without_private_key(monkeypatch):
    monkeypatch.delenv("APPFORGE_BUILD_TOKEN", raising=False)
    response = TestClient(app).post(
        "/api/appforge/build",
        json={"files": {"index.html": "<!doctype html><html></html>"}},
    )
    assert response.status_code == 503


def test_appforge_build_requires_private_key(monkeypatch):
    monkeypatch.setenv("APPFORGE_BUILD_TOKEN", "test-private-key")
    response = TestClient(app).post(
        "/api/appforge/build",
        json={"files": {"index.html": "<!doctype html><html></html>"}},
    )
    assert response.status_code == 401


def test_appforge_build_runs_through_isolated_runner(monkeypatch):
    import backend.appforge_sandbox as sandbox_runner

    monkeypatch.setenv("APPFORGE_BUILD_TOKEN", "test-private-key")

    async def fake_build(files):
        assert files["index.html"].startswith("<!doctype html>")
        return {
            "ok": True,
            "status": "built",
            "files": 1,
            "preview_html": files["index.html"],
            "isolation": "ephemeral-microvm-network-restricted",
        }

    monkeypatch.setattr(sandbox_runner, "run_isolated_build", fake_build)
    response = TestClient(app).post(
        "/api/appforge/build",
        headers={"X-AppForge-Build-Key": "test-private-key"},
        json={"files": {"index.html": "<!doctype html><html><body>Built</body></html>"}},
    )
    assert response.status_code == 200
    assert response.json()["isolation"] == "ephemeral-microvm-network-restricted"



def test_appforge_export_returns_zip_for_multi_file_project():
    from io import BytesIO
    from zipfile import ZipFile

    response = TestClient(app).post(
        "/api/appforge/export",
        json={
            "project_name": "Demo App",
            "files": {
                "index.html": "<!doctype html><html><body>Demo</body></html>",
                "styles/app.css": "body { color: teal; }",
                "src/app.js": "console.log('demo');",
            },
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/zip")
    with ZipFile(BytesIO(response.content)) as archive:
        assert set(archive.namelist()) == {"index.html", "styles/app.css", "src/app.js"}
        assert b"Demo" in archive.read("index.html")


def test_appforge_export_rejects_path_traversal():
    response = TestClient(app).post(
        "/api/appforge/export",
        json={"project_name": "Demo", "files": {"../escape.js": "alert(1)", "index.html": "<html></html>"}},
    )
    assert response.status_code == 422

def test_appforge_preview_detects_complete_html_with_whitespace():
    source = (ROOT / "appforge" / "app.js").read_text(encoding="utf-8")
    assert r"/<(?:!doctype\s+html|html)(?:\s|>)/i" in source
    assert r"/<\/html\s*>/i" in source
