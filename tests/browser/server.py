"""Isolated HTTP fixture for browser regression, with no external credentials."""
import asyncio
import os

from backend import app as runtime

os.environ.update({
    "SAARTHI_ENV": "local", "SAARTHI_ORIGIN": "http://127.0.0.1:8765",
    "SAARTHI_OWNER_ID": "browser-fixture", "SAARTHI_OWNER_PASSWORD": "browser-fixture-password-1234",
    "SAARTHI_SESSION_KEY": "browser-fixture-only-signing-material",
    "SAARTHI_DAILY_TURNS": "1000",
})
from backend.passwords import hash_password
os.environ["SAARTHI_OWNER_PASSWORD_HASH"] = hash_password("browser-fixture-password-1234")

turns: dict = {}


async def scope(environment):
    assert environment == "local"


async def begin(owner, thread, turn, message, fingerprint, limit):
    row = turns.get((owner, turn))
    if row:
        return {"decision": row["state"], "result": row.get("result")}
    turns[(owner, turn)] = {"thread": thread, "state": "pending", "message": message}
    return {"decision": "started"}


async def finish(owner, turn, state, result):
    row = turns.get((owner, turn))
    if not row or row["state"] != "pending":
        return False
    row.update(state=state, result=dict(result))
    return True


async def recent(owner, thread):
    return [row for (uid, _), row in reversed(list(turns.items()))
            if uid == owner and row["thread"] == thread and row["state"] == "completed"][:10]


async def worker(payload, budget):
    await asyncio.sleep(0.12)
    message = payload["message"]
    if message == "fixture-cancel":
        await asyncio.sleep(10)
    if message == "fixture-deadline":
        raise TimeoutError
    if message == "fixture-code":
        reply = "```python\nprint('saarthi')\n```"
    elif message.startswith("fixture-file:"):
        reply = "Included " + ", ".join(item["name"] for item in payload["context"]["attachments"])
    else:
        reply = "Reply to " + message
    return {"ok": True, "reply": reply, "execution": "completed",
            "provider": "browser-fixture", "verification": {"verified": False}}


runtime.store.check_scope = scope
runtime.store.begin_turn = begin
runtime.store.recent_turns = recent
async def turn_result(owner, turn):
    return turns.get((owner, turn))


runtime.store.finish_turn = finish
runtime.store.turn_result = turn_result
runtime.run_turn = worker
app = runtime.app


# This module is only the isolated browser-test app, never the deployed entrypoint.
import hashlib
from fastapi import Request

os.environ["SAARTHI_OWNER_AUTH_STORE"] = "database"
initial_password = hash_password("browser-fixture-password-1234")
os.environ.pop("SAARTHI_OWNER_PASSWORD", None)
os.environ.pop("SAARTHI_OWNER_PASSWORD_HASH", None)
owner_state = {"credential": initial_password, "grant": None}


async def owner_password(owner):
    return owner_state["credential"]


async def claim_login(owner):
    return True


async def management(token):
    return token == "browser-management-fixture"


async def issue_grant(owner, digest, intent, legacy):
    if intent == "setup" and owner_state["credential"]:
        return False
    owner_state["grant"] = digest
    return True


async def complete_setup(owner, digest, encoded, legacy):
    if owner_state["grant"] != digest:
        return False
    owner_state.update(credential=encoded, grant=None)
    return True


@app.post("/fixture/clear-owner")
async def clear_owner():
    owner_state.update(credential=None, grant=None)
    return {"ok": True}


runtime.store.owner_password = owner_password
runtime.store.claim_login = claim_login
runtime.store.issue_owner_grant = issue_grant
runtime.store.complete_owner_setup = complete_setup
runtime.verify_deployment_access = management


@app.post("/fixture/reset-rate")
async def reset_rate():
    runtime._rate_buckets.clear()
    return {"ok": True}
