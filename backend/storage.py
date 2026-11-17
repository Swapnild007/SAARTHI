from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

from .deployment import SpendLimits, storage_endpoint
from urllib.request import Request, urlopen
import json
from urllib.parse import urlsplit


class CloudStore:
    """Small PostgREST adapter. Uses Supabase/PostgREST when configured.

    Required:
      SAARTHI_SUPABASE_URL
      SAARTHI_SUPABASE_SERVICE_ROLE_KEY

    The browser never receives the service-role key.
    """

    def __init__(self) -> None:
        self.url, self.key = storage_endpoint()

    @property
    def configured(self) -> bool:
        return bool(self.url and self.key)

    def _request(self, path: str, *, method: str = "GET", payload: Any = None, query: str = "") -> Any:
        if not self.configured:
            raise RuntimeError("cloud store is not configured")
        url = f"{self.url}/rest/v1/{path}"
        if query:
            url += f"?{query}"
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if method in {"POST", "PATCH"}:
            headers["Prefer"] = "return=representation"
        req = Request(url, data=body, headers=headers, method=method)
        with urlopen(req, timeout=8) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else None

    @staticmethod
    def user_id(session_id: str) -> str:
        # Stable anonymous account per browser session. No email/PII required.
        return str(uuid.uuid5(uuid.NAMESPACE_URL, "saarthi-session:" + session_id))

    def ensure_user(self, user_id: str) -> None:
        rows = self._request("users", query=f"id=eq.{user_id}&select=id&limit=1")
        if not rows:
            self._request("users", method="POST", payload={"id": user_id})

    def save_turn(
        self,
        *,
        session_id: str,
        conversation_id: str,
        user_content: str,
        assistant_content: str,
        title: str | None = None,
    ) -> str:
        user_id = self.user_id(session_id)
        self.ensure_user(user_id)
        try:
            cid = str(uuid.UUID(conversation_id))
        except (ValueError, AttributeError):
            cid = str(uuid.uuid5(uuid.NAMESPACE_URL, "saarthi-conversation:" + conversation_id))

        existing = self._request("conversations", query=f"id=eq.{cid}&select=id&limit=1")
        if not existing:
            self._request("conversations", method="POST", payload={
                "id": cid,
                "user_id": user_id,
                "title": (title or user_content[:120]).strip()[:200],
            })
        else:
            self._request("conversations", method="PATCH", query=f"id=eq.{cid}", payload={
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })

        self._request("messages", method="POST", payload=[
            {"conversation_id": cid, "role": "user", "content": user_content[:12000]},
            {"conversation_id": cid, "role": "assistant", "content": assistant_content[:20000]},
        ])
        return cid

    def conversations(self, session_id: str, limit: int = 50) -> list[dict[str, Any]]:
        user_id = self.user_id(session_id)
        rows = self._request(
            "conversations",
            query=f"user_id=eq.{user_id}&select=id,title,created_at,updated_at&order=updated_at.desc&limit={max(1,min(limit,100))}",
        )
        return rows if isinstance(rows, list) else []

    def messages(self, session_id: str, conversation_id: str, limit: int = 100) -> list[dict[str, Any]]:
        user_id = self.user_id(session_id)
        conv = self._request("conversations", query=f"id=eq.{conversation_id}&user_id=eq.{user_id}&select=id&limit=1")
        if not conv:
            return []
        rows = self._request(
            "messages",
            query=f"conversation_id=eq.{conversation_id}&select=id,role,content,created_at&order=created_at.asc&limit={max(1,min(limit,200))}",
        )
        return rows if isinstance(rows, list) else []

    def save_memory(self, session_id: str, memory_type: str, content: str, importance: float = 0.5) -> dict[str, Any]:
        user_id = self.user_id(session_id)
        self.ensure_user(user_id)
        row = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "memory_type": str(memory_type or "general")[:80],
            "content": str(content)[:5000],
            "importance": max(0.0, min(float(importance), 1.0)),
        }
        result = self._request("memories", method="POST", payload=row)
        return (result[0] if isinstance(result, list) and result else row)

    def memories(self, session_id: str, limit: int = 50) -> list[dict[str, Any]]:
        user_id = self.user_id(session_id)
        rows = self._request(
            "memories",
            query=f"user_id=eq.{user_id}&select=id,memory_type,content,importance,created_at,updated_at&order=updated_at.desc&limit={max(1,min(limit,100))}",
        )
        return rows if isinstance(rows, list) else []


    async def recovery_request(
        self, path: str, *, method: str = "GET", payload: Any = None, params: dict | None = None,
    ) -> Any:
        if not self.configured:
            raise RuntimeError("Conversation storage is unavailable")
        parsed = urlsplit(self.url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
            raise RuntimeError("Conversation storage URL is invalid")
        async with httpx.AsyncClient(timeout=2.0, follow_redirects=False) as client:
            response = await client.request(
                method, f"{self.url}/rest/v1/{path}", json=payload, params=params,
                headers={
                    "apikey": self.key, "Authorization": f"Bearer {self.key}",
                    "Prefer": "return=representation",
                },
            )
            if not response.is_success:
                raise RuntimeError("Conversation storage rejected the operation")
            return response.json() if response.content else None

    async def check_scope(self, environment: str) -> None:
        rows = await self.recovery_request("saarthi_scope", params={"select": "environment"})
        if rows != [{"environment": environment}]:
            raise RuntimeError("Conversation storage belongs to another environment")

    async def owner_password(self, owner: str) -> str | None:
        rows = await self.recovery_request("saarthi_owner_credentials", params={
            "owner": f"eq.{owner}", "select": "password_hash", "limit": 1,
        })
        return rows[0]["password_hash"] if rows else None

    async def issue_owner_grant(self, owner: str, token_hash: str, intent: str, legacy: str) -> bool:
        return await self.recovery_request("rpc/saarthi_issue_owner_grant", method="POST", payload={
            "p_owner": owner, "p_token_hash": token_hash, "p_intent": intent, "p_legacy_hash": legacy,
        }) is True

    async def complete_owner_setup(self, owner: str, token_hash: str, password_hash: str, legacy: str) -> bool:
        return await self.recovery_request("rpc/saarthi_complete_owner_setup", method="POST", payload={
            "p_owner": owner, "p_token_hash": token_hash, "p_password_hash": password_hash, "p_legacy_hash": legacy,
        }) is True

    async def begin_turn(self, owner: str, thread: str, turn: str, message: str, fingerprint: str, limit: int) -> dict:
        return await self.recovery_request("rpc/saarthi_begin_turn", method="POST", payload={
            "p_owner": owner, "p_conversation": thread, "p_turn": turn,
            "p_message": message, "p_fingerprint": fingerprint, "p_daily_limit": limit,
        })

    async def admit_turn(self, owner: str, thread: str, turn: str, message: str, fingerprint: str,
                         limit: int, spend: SpendLimits) -> dict:
        return await self.recovery_request("rpc/saarthi_admit_turn", method="POST", payload={
            "p_owner": owner, "p_conversation": thread, "p_turn": turn,
            "p_message": message, "p_fingerprint": fingerprint, "p_daily_limit": limit,
            "p_reserve": spend.reserve, "p_day_cap": spend.daily, "p_month_cap": spend.monthly,
        })

    async def report_cost(self, owner: str, turn: str, micro_usd: int) -> None:
        await self.recovery_request("saarthi_spend", method="PATCH", params={
            "owner": f"eq.{owner}", "turn_id": f"eq.{turn}",
        }, payload={"reported_micro_usd": micro_usd})

    async def claim_login(self, owner: str) -> bool:
        return await self.recovery_request("rpc/saarthi_claim_login", method="POST",
                                           payload={"p_owner": owner}) is True

    async def finish_turn(self, owner: str, turn: str, state: str, result: dict) -> bool:
        rows = await self.recovery_request(
            "saarthi_turns", method="PATCH",
            params={"owner": f"eq.{owner}", "turn_id": f"eq.{turn}", "state": "eq.pending"},
            payload={"state": state, "result": result},
        )
        return bool(rows)

    async def turn_result(self, owner: str, turn: str) -> dict | None:
        rows = await self.recovery_request("saarthi_turns", params={
            "owner": f"eq.{owner}", "turn_id": f"eq.{turn}", "select": "state,result", "limit": 1,
        })
        return rows[0] if rows else None

    async def recent_turns(self, owner: str, thread: str) -> list[dict]:
        return await self.recovery_request("saarthi_turns", params={
            "owner": f"eq.{owner}", "conversation_id": f"eq.{thread}", "state": "eq.completed",
            "select": "message,result", "order": "seq.desc", "limit": 10,
        })

    async def recovery_threads(self, owner: str, offset: int, limit: int) -> list[dict]:
        return await self.recovery_request("saarthi_threads", params={
            "owner": f"eq.{owner}", "select": "id,title,updated_at", "order": "updated_at.desc,id",
            "limit": limit, "offset": offset,
        })

    async def recovery_turns(self, owner: str, thread: str, after: int, limit: int) -> list[dict]:
        return await self.recovery_request("saarthi_turns", params={
            "owner": f"eq.{owner}", "conversation_id": f"eq.{thread}", "seq": f"gt.{after}",
            "select": "turn_id,seq,message,state,result,created_at", "order": "seq.asc", "limit": limit,
        })

    async def update_thread(self, owner: str, thread: str, title: str | None) -> bool:
        rows = await self.recovery_request("saarthi_threads", method="PATCH" if title else "DELETE",
            params={"owner": f"eq.{owner}", "id": f"eq.{thread}"}, payload={"title": title} if title else None)
        return bool(rows)


def store_status(store: CloudStore) -> dict[str, Any]:
    return {
        "configured": store.configured,
        "provider": "supabase-postgrest" if store.configured else "unconfigured",
    }