from fastapi.testclient import TestClient

from backend.app import app


def test_appforge_project_sync_falls_back_when_cloud_store_is_unconfigured(monkeypatch):
    class Store:
        configured = False

    monkeypatch.setattr(app.state, "cloud_store", Store(), raising=False)
    session_id = "11111111-1111-4111-8111-111111111111"
    client = TestClient(app, headers={"X-SAARTHI-Access":"test-access"})

    listed = client.get("/api/appforge/projects", params={"session_id": session_id})
    assert listed.status_code == 200
    assert listed.json()["provider"] == "browser-local"
    assert listed.json()["projects"] == []

    saved = client.post(
        "/api/appforge/projects",
        json={
            "session_id": session_id,
            "project": {"id": "6e3a1c9d-7bb3-4b80-a72e-cbd0d8cc8c4a", "name": "Demo", "html": "<html></html>"},
        },
    )
    assert saved.status_code == 200
    assert saved.json()["saved"] is False


def test_appforge_project_sync_uses_managed_store_when_configured(monkeypatch):
    class Store:
        configured = True

        def __init__(self):
            self.saved = None

        def save_appforge_project(self, session_id, project):
            self.saved = (session_id, project)
            return {"project_id": project["id"]}

        def appforge_projects(self, session_id, limit=30):
            return [{
                "project_id": "6e3a1c9d-7bb3-4b80-a72e-cbd0d8cc8c4a",
                "name": "Demo",
                "prompt": "demo prompt",
                "html": "<!doctype html><html></html>",
                "versions": [],
                "created_at": "2026-10-19T00:00:00+00:00",
                "updated_at": "2026-10-19T00:00:00+00:00",
            }]

        def delete_appforge_project(self, session_id, project_id):
            return project_id == "6e3a1c9d-7bb3-4b80-a72e-cbd0d8cc8c4a"

    monkeypatch.setenv("SAARTHI_ACCESS_TOKEN", "test-access")
    store = Store()
    monkeypatch.setattr(app.state, "cloud_store", store, raising=False)
    session_id = "11111111-1111-4111-8111-111111111111"
    client = TestClient(app, headers={"X-SAARTHI-Access":"test-access"})

    saved = client.post(
        "/api/appforge/projects",
        json={
            "session_id": session_id,
            "project": {
                "id": "6e3a1c9d-7bb3-4b80-a72e-cbd0d8cc8c4a",
                "name": "Demo",
                "prompt": "demo prompt",
                "html": "<!doctype html><html></html>",
                "versions": [],
            },
        },
    )
    assert saved.status_code == 200
    assert saved.json()["saved"] is True
    assert store.saved[0] == session_id

    listed = client.get("/api/appforge/projects", params={"session_id": session_id})
    assert listed.status_code == 200
    assert listed.json()["projects"][0]["name"] == "Demo"

    deleted = client.delete(
        "/api/appforge/projects/6e3a1c9d-7bb3-4b80-a72e-cbd0d8cc8c4a",
        params={"session_id": session_id},
    )
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True
