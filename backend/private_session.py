"""Server-issued private owner sessions with deployment-scoped credentials."""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import time
from dataclasses import dataclass
from urllib.parse import urlsplit

from .deployment import hosted, setting
from .passwords import valid_hash, verify_password

COOKIE = "saarthi_owner"
TTL = 3600


@dataclass(frozen=True)
class Scope:
    environment: str
    origin: str
    commit: str
    owner: str
    password: str
    signing_key: str
    daily_turns: int

    @classmethod
    def read(cls) -> Scope | None:
        environment = os.getenv("SAARTHI_ENV", "")
        if environment not in {"local", "preview", "staging", "production"}:
            return None
        platform = os.getenv("VERCEL_ENV")
        if os.getenv("VERCEL") and not platform:
            return None
        if platform and environment != platform and not (platform == "preview" and environment == "staging"):
            return None
        origin = os.getenv("SAARTHI_ORIGIN", "").rstrip("/")
        try:
            parsed = urlsplit(origin)
            if not parsed.hostname or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
                return None
            if environment == "local":
                if hosted() or parsed.hostname not in {"localhost", "127.0.0.1", "::1"} or parsed.scheme not in {"http", "https"}:
                    return None
            elif parsed.scheme != "https":
                return None
            turns = int(os.getenv("SAARTHI_DAILY_TURNS", "100"))
        except ValueError:
            return None
        commit = os.getenv("VERCEL_GIT_COMMIT_SHA") or os.getenv("SAARTHI_COMMIT_SHA", "")
        if environment != "local" and not re.fullmatch(r"[a-f0-9]{40}", commit):
            return None
        owner = setting("OWNER_ID")
        password_hash = setting("OWNER_PASSWORD_HASH")
        if password_hash and not valid_hash(password_hash):
            return None
        password = password_hash or setting("OWNER_PASSWORD")
        signing_key = setting("SESSION_KEY")
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", owner) or len(password) < 24 or len(signing_key) < 32:
            return None
        if not 1 <= turns <= 1000:
            return None
        return cls(environment, origin, commit, owner, password, signing_key, turns)

    def verify_password(self, password: str) -> bool:
        if valid_hash(self.password):
            return verify_password(password, self.password)
        return hmac.compare_digest(password.encode(), self.password.encode())

    def _signature(self, data: str) -> str:
        bound = f"{self.environment}|{self.origin}|{self.owner}|{self.password}|{data}"
        return hmac.new(self.signing_key.encode(), bound.encode(), hashlib.sha256).hexdigest()

    def issue(self) -> str:
        value = f"{int(time.time()) + TTL}.{secrets.token_hex(16)}"
        return f"{value}.{self._signature(value)}"

    def authenticated(self, token: str) -> bool:
        if not re.fullmatch(r"\d{1,12}\.[a-f0-9]{32}\.[a-f0-9]{64}", token):
            return False
        value, signature = token.rsplit(".", 1)
        return int(value.split(".", 1)[0]) > time.time() and hmac.compare_digest(signature, self._signature(value))
