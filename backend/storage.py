from __future__ import annotations

import hashlib
import os
import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.request import Request, urlopen
import json


class CloudStore:
    """Small PostgREST adapter. Uses Supabase/PostgREST when configured.

    Required:
      SAARTHI_SUPABASE_URL
      SAARTHI_SUPABASE_SERVICE_ROLE_KEY

    The browser never receives the service-role key.
    """

    def __init__(self) -> None:
        self.url = os.getenv("SAARTHI_SUPABASE_URL", "").rstrip("/")
        self.key = os.getenv("SAARTHI_SUPABASE_SERVICE_ROLE_KEY", "").strip()

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


def store_status(store: CloudStore) -> dict[str, Any]:
    return {
        "configured": store.configured,
        "provider": "supabase-postgrest" if store.configured else "unconfigured",
    }
