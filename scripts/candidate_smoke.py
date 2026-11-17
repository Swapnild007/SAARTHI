"""Validate a private candidate and a staged rollback using synthetic threads."""
import os
import re
import secrets
from urllib.parse import urlsplit
from uuid import uuid4

import httpx


def approved_origin(url: str, approved: str) -> str:
    parsed = urlsplit(url)
    if (url != approved or parsed.scheme != "https" or not parsed.hostname
            or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path):
        raise ValueError("A matching approved private HTTPS origin is required")
    return url


def require(condition: bool, issue: str) -> None:
    if not condition:
        raise RuntimeError(issue)


def login(client: httpx.Client, environment: str, sha: str, password: str) -> None:
    require(environment in {"preview", "staging"} and bool(re.fullmatch(r"[a-f0-9]{40}", sha)),
            "An exact private deployment SHA is required")
    health = client.get("/api/health").raise_for_status().json()
    require(health["ok"] and health["environment"] == environment and health["commit"] == sha,
            "Deployment scope or SHA mismatch")
    require(health["provider_configured"] and health["python"].startswith("3.12."),
            "Runtime or provider is unconfigured")
    require(client.get("/api/persistence").status_code == 401, "Unauthenticated persistence is accessible")
    client.post("/api/session/login", json={"password": password}).raise_for_status()
    client.get("/api/persistence").raise_for_status()


def send(client: httpx.Client, payload: dict, provider: str) -> dict:
    result = client.post("/api/command", json=payload).raise_for_status().json()
    require(result.get("ok") is True and result.get("execution") == "completed" and
            result.get("response_source") == "upstream" and result.get("provider") == provider and
            result.get("turn_id") == payload["turn_id"] and
            result.get("conversation_id") == payload["conversation_id"] and
            isinstance(result.get("reply"), str) and bool(result["reply"].strip()),
            "Upstream execution or response correlation failed")
    return result


def history(client: httpx.Client, thread: str) -> list[dict]:
    after = 0
    rows = []
    while after is not None:
        page = client.get(f"/api/conversations/{thread}/messages",
                          params={"after": after, "limit": 5}).raise_for_status().json()
        rows.extend(page["turns"])
        cursor = page["next_after"]
        require(cursor is None or isinstance(cursor, int) and cursor > after, "History cursor stalled")
        after = cursor
    return rows


def exercise(client: httpx.Client, thread: str, provider: str, turns: int) -> list[dict]:
    recall = secrets.token_hex(8)
    prompts = [f"Keep this marker in this conversation: {recall}. Acknowledge it.",
               "What exact marker did I give you in the previous message? Reply with only the marker."]
    prompts.extend(f"Reply with the text CHECKPOINT {index}." for index in range(2, turns))
    expected = []
    for prompt in prompts:
        payload = {"message": prompt, "conversation_id": thread, "turn_id": str(uuid4())}
        reply = send(client, payload, provider)
        if len(expected) == 1:
            require(recall in reply["reply"], "Multi-turn marker was not recalled")
        expected.append((payload, reply))
    payload, reply = expected[-1]
    require(send(client, payload, provider) == reply, "A same-turn retry changed the terminal result")
    rows = history(client, thread)
    require([(r["turn_id"], r["message"], r["result"]["reply"]) for r in rows] ==
            [(p["turn_id"], p["message"], r["reply"]) for p, r in expected],
            "Paginated transcript does not match the submitted turns")
    return rows


def main() -> None:
    url = approved_origin(os.environ["SAARTHI_CANDIDATE_URL"], os.environ["SAARTHI_APPROVED_URL"])
    environment = os.environ["SAARTHI_CANDIDATE_ENV"]
    sha = os.environ["SAARTHI_CANDIDATE_SHA"]
    provider = os.environ["SAARTHI_EXPECTED_PROVIDER"]
    password = os.environ["SAARTHI_CANDIDATE_PASSWORD"]
    turns = int(os.getenv("SAARTHI_SMOKE_TURNS", "2"))
    require(provider in {"ai-gateway"} and 2 <= turns <= 20, "Unsupported provider or turn count")
    thread = "smoke-" + secrets.token_hex(12)
    rollback_url = os.getenv("SAARTHI_ROLLBACK_URL", "")
    with httpx.Client(base_url=url, timeout=35, follow_redirects=False) as client:
        login(client, environment, sha, password)
        try:
            rows = exercise(client, thread, provider, turns)
            with httpx.Client(base_url=url, timeout=35, follow_redirects=False) as fresh:
                login(fresh, environment, sha, password)
                require(history(fresh, thread) == rows, "Fresh-session restoration failed")
            if rollback_url:
                require(environment == "staging", "Rollback requires staging")
                rollback = approved_origin(rollback_url, os.environ["SAARTHI_APPROVED_ROLLBACK_URL"])
                older_sha = os.environ["SAARTHI_ROLLBACK_SHA"]
                require(older_sha != sha and rollback != url, "Rollback requires a distinct compatible staging build")
                with httpx.Client(base_url=rollback, timeout=35, follow_redirects=False) as older:
                    login(older, "staging", older_sha, os.environ["SAARTHI_ROLLBACK_PASSWORD"])
                    require(history(older, thread) == rows, "Rollback build did not restore staging history")
                    result = send(older, {"message": "Reply with ROLLBACK READY.", "conversation_id": thread,
                                          "turn_id": str(uuid4())}, provider)
                    require(history(client, thread)[-1]["turn_id"] == result["turn_id"],
                            "Rollback write was not visible from the candidate")
        finally:
            response = client.delete(f"/api/conversations/{thread}")
            require(response.status_code in {200, 404}, "Synthetic thread cleanup failed")
        require(history(client, thread) == [], "Deleted thread was still readable")
    print(f"Verified private candidate {sha} on {environment}, {turns} upstream turns, rollback evidence: {bool(rollback_url)}")


if __name__ == "__main__":
    main()
