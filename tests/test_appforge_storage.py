from backend.storage import CloudStore


def test_cloud_store_upserts_project_with_user_scoped_identity(monkeypatch):
    store = CloudStore()
    store.url = "https://example.supabase.co"
    store.key = "test-key"
    calls = []

    def fake_request(path, *, method="GET", payload=None, query="", prefer=None):
        calls.append((path, method, payload, query, prefer))
        if path == "users" and method == "GET":
            return []
        if path == "appforge_projects":
            return [{"project_id": payload["project_id"]}]
        return []

    monkeypatch.setattr(store, "_request", fake_request)
    monkeypatch.setattr(store, "ensure_user", lambda user_id: calls.append(("ensure_user", user_id)))

    session_id = "11111111-1111-4111-8111-111111111111"
    project = {
        "id": "6e3a1c9d-7bb3-4b80-a72e-cbd0d8cc8c4a",
        "name": "Demo",
        "prompt": "Build a demo",
        "html": "<!doctype html><html></html>",
        "versions": [],
    }
    result = store.save_appforge_project(session_id, project)

    assert result["project_id"] == project["id"]
    save_call = next(call for call in calls if call[0] == "appforge_projects")
    assert save_call[1] == "POST"
    assert save_call[3] == "on_conflict=user_id,project_id"
    assert save_call[4] == "resolution=merge-duplicates,return=representation"
    assert save_call[2]["name"] == "Demo"
    assert save_call[2]["user_id"] == store.user_id(session_id)


def test_cloud_store_project_queries_are_scoped_to_derived_user(monkeypatch):
    store = CloudStore()
    store.url = "https://example.supabase.co"
    store.key = "test-key"
    calls = []

    def fake_request(path, *, method="GET", payload=None, query="", prefer=None):
        calls.append((path, method, query))
        return []

    monkeypatch.setattr(store, "_request", fake_request)
    session_id = "11111111-1111-4111-8111-111111111111"
    store.appforge_projects(session_id)
    store.delete_appforge_project(session_id, "6e3a1c9d-7bb3-4b80-a72e-cbd0d8cc8c4a")

    user_id = store.user_id(session_id)
    assert f"user_id=eq.{user_id}" in calls[0][2]
    assert f"user_id=eq.{user_id}" in calls[1][2]
    assert "project_id=eq.6e3a1c9d-7bb3-4b80-a72e-cbd0d8cc8c4a" in calls[1][2]
