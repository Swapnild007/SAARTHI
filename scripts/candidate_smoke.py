"""Private staging smoke. Rejects production and verifies real model continuity."""
import os
import secrets
from urllib.parse import urlsplit

import httpx

url = os.environ["SAARTHI_CANDIDATE_URL"].rstrip("/")
environment = os.environ["SAARTHI_CANDIDATE_ENV"]
commit = os.environ["SAARTHI_CANDIDATE_SHA"]
provider = os.environ["SAARTHI_EXPECTED_PROVIDER"]

if urlsplit(url).scheme != "https" or environment not in {"preview", "staging"}:
    raise SystemExit("Smoke requires HTTPS and a private preview or staging environment")
if not provider or provider in {"deterministic-fallback", "fixture", "browser-fixture"}:
    raise SystemExit("Smoke requires the intended live provider")

with httpx.Client(base_url=url, timeout=35, follow_redirects=False) as client:
    health = client.get("/api/health").raise_for_status().json()
    assert health["ok"] and health["environment"] == environment and health["commit"] == commit
    assert health["provider_configured"] and health["python"].startswith("3.12.")
    client.post("/api/session/login", json={"password": os.environ["SAARTHI_CANDIDATE_PASSWORD"]}).raise_for_status()
    thread = "smoke-" + secrets.token_hex(12)
    recall = secrets.token_hex(8)
    try:
        client.get("/api/persistence").raise_for_status()
        prompts = [
            f"Remember this marker for the next turn in this chat: {recall}. Reply that you have noted the marker.",
            "What exact marker did I give you in my last message? Reply with only the marker.",
        ]
        for prompt in prompts:
            result = client.post("/api/command", json={"message": prompt, "conversation_id": thread}).raise_for_status().json()
            assert result["ok"] and result["execution"] == "completed" and result["provider"] == provider
            assert result["turn_id"] and result["conversation_id"] == thread and result["reply"].strip()
        assert recall in result["reply"]
        history = client.get(f"/api/conversations/{thread}/messages?limit=1").raise_for_status().json()
        assert len(history["turns"]) == 1 and history["turns"][0]["message"] == prompts[0]
        second = client.get(f"/api/conversations/{thread}/messages", params={"after": history["next_after"]}).raise_for_status().json()
        assert len(second["turns"]) == 1 and second["turns"][0]["result"]["reply"] == result["reply"]
    finally:
        response = client.delete(f"/api/conversations/{thread}")
        assert response.status_code in (200, 404)
print(f"Verified private candidate {commit} on {environment} with {provider}")
