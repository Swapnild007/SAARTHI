from __future__ import annotations
import hashlib, json, os, re, hmac, sqlite3
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

MAX_CHUNK_CHARS = 1800
CHUNK_OVERLAP = 240

def chunk_text(text: str, *, max_chars: int = MAX_CHUNK_CHARS, overlap: int = CHUNK_OVERLAP) -> list[str]:
    value = re.sub(r"\r\n?", "\n", str(text or "")).strip()
    if not value:
        return []
    max_chars = max(300, min(int(max_chars), 5000))
    overlap = max(0, min(int(overlap), max_chars // 3))
    chunks, start = [], 0
    while start < len(value):
        end = min(len(value), start + max_chars)
        if end < len(value):
            boundary = max(value.rfind("\n", start + max_chars // 2, end),
                           value.rfind(". ", start + max_chars // 2, end))
            if boundary > start:
                end = boundary + 1
        part = value[start:end].strip()
        if part:
            chunks.append(part)
        if end >= len(value):
            break
        start = max(start + 1, end - overlap)
    return chunks

def _config() -> dict[str, str]:
    return {"db_url": os.getenv("SAARTHI_SUPABASE_URL", "").rstrip("/"),
            "db_key": os.getenv("SAARTHI_SUPABASE_SERVICE_ROLE_KEY", "").strip(),
            "embedding_url": os.getenv("SAARTHI_EMBEDDING_API_URL", "").rstrip("/"),
            "embedding_key": os.getenv("SAARTHI_EMBEDDING_API_KEY", "").strip(),
            "embedding_model": os.getenv("SAARTHI_EMBEDDING_MODEL", "").strip()}

def _local_db_path() -> Path:
    configured = os.getenv("SAARTHI_LOCAL_KNOWLEDGE_DB", "").strip()
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".saarthi" / "knowledge.sqlite3"


def _local_connection() -> sqlite3.Connection:
    path = _local_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path), timeout=5)
    connection.row_factory = sqlite3.Row
    connection.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_chunks (
            id TEXT PRIMARY KEY, collection TEXT NOT NULL, title TEXT NOT NULL,
            source TEXT NOT NULL, chunk_index INTEGER NOT NULL, content TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    connection.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_collection ON knowledge_chunks(collection)")
    return connection


def _managed_configured(c: dict[str, str]) -> bool:
    return all(c[k] for k in ("db_url", "db_key", "embedding_url", "embedding_key", "embedding_model"))


def status() -> dict[str, Any]:
    c = _config()
    if _managed_configured(c):
        return {"configured": True, "provider": "Supabase pgvector + OpenAI-compatible embeddings",
                "mode": "managed-semantic", "missing_configuration": [], "self_hosted_server_required": False}
    try:
        with _local_connection() as connection:
            connection.execute("SELECT 1")
        return {"configured": True, "provider": "SQLite local lexical retrieval",
                "mode": "local-offline",
                "missing_configuration": [], "self_hosted_server_required": False}
    except (OSError, sqlite3.Error):
        return {"configured": False, "provider": "not_configured", "mode": "unavailable",
                "missing_configuration": ["local knowledge database is not writable"],
                "self_hosted_server_required": False}

def _request(url: str, key: str, *, payload: Any = None, timeout: float = 7.0) -> Any:
    req = Request(url, data=json.dumps(payload).encode("utf-8") if payload is not None else None,
        method="POST", headers={"Content-Type": "application/json", "Accept": "application/json",
        "apikey": key, "Authorization": "Bearer " + key, "Prefer": "resolution=merge-duplicates,return=representation"})
    try:
        with urlopen(req, timeout=timeout) as response:
            raw = response.read(2_000_000).decode("utf-8", errors="replace")
            return json.loads(raw) if raw else None
    except HTTPError as exc:
        raise RuntimeError(f"Knowledge provider returned HTTP {exc.code}") from None
    except (URLError, TimeoutError, OSError, json.JSONDecodeError):
        raise RuntimeError("Knowledge provider unavailable or timed out") from None

def embed(texts: list[str]) -> list[list[float]]:
    c = _config()
    if not c["embedding_url"] or not c["embedding_key"] or not c["embedding_model"]:
        raise RuntimeError("embedding provider is not configured")
    endpoint = c["embedding_url"]
    if not endpoint.endswith("/embeddings"):
        endpoint += "/embeddings"
    req = Request(endpoint, data=json.dumps({"model": c["embedding_model"], "input": texts}).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + c["embedding_key"]}, method="POST")
    try:
        with urlopen(req, timeout=4.0) as response:
            body = json.loads(response.read(2_000_000).decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"Embedding provider returned HTTP {exc.code}") from None
    except Exception:
        raise RuntimeError("Embedding provider unavailable or timed out") from None
    data = body.get("data", []) if isinstance(body, dict) else []
    data.sort(key=lambda item: int(item.get("index", 0)))
    vectors = [item.get("embedding") for item in data if isinstance(item, dict)]
    if len(vectors) != len(texts) or any(not isinstance(v, list) or not v for v in vectors):
        raise RuntimeError("Embedding provider returned an unexpected vector shape")
    if any(len(vector) != 1536 for vector in vectors):
        raise RuntimeError("Embedding dimension mismatch: database schema expects 1536 dimensions")
    return vectors

def ingest_text(text: str, *, title: str, source: str = "", collection: str = "default") -> dict[str, Any]:
    c = _config()
    chunks = chunk_text(text)
    if not chunks:
        raise ValueError("No text content to index")
    if not _managed_configured(c):
        rows = []
        for index, part in enumerate(chunks):
            digest = hashlib.sha256((collection + "\\0" + source + "\\0" + str(index) + "\\0" + part).encode()).hexdigest()
            rows.append((digest, collection[:100], title[:300], source[:1000], index, part))
        with _local_connection() as connection:
            connection.executemany(
                "INSERT INTO knowledge_chunks(id,collection,title,source,chunk_index,content) VALUES(?,?,?,?,?,?) "
                "ON CONFLICT(id) DO UPDATE SET title=excluded.title,source=excluded.source,content=excluded.content",
                rows,
            )
        return {"indexed": len(rows), "title": title[:300], "collection": collection[:100],
                "provider": "sqlite-local", "semantic": False}
    vectors = embed(chunks)
    rows = []
    for index, (part, vector) in enumerate(zip(chunks, vectors)):
        digest = hashlib.sha256((collection + "\0" + source + "\0" + str(index) + "\0" + part).encode()).hexdigest()
        rows.append({"id": digest, "collection": collection[:100], "title": title[:300],
                     "source": source[:1000], "chunk_index": index, "content": part, "embedding": vector})
    _request(c["db_url"] + "/rest/v1/knowledge_chunks?on_conflict=id", c["db_key"], payload=rows, timeout=10.0)
    return {"indexed": len(rows), "title": title[:300], "collection": collection[:100]}

def search(query: str, *, limit: int = 5, collection: str = "default") -> list[dict[str, Any]]:
    c = _config()
    if not _managed_configured(c):
        terms = list(dict.fromkeys(re.findall(r"[\w'-]{2,}", query.casefold())))
        if not terms:
            return []
        with _local_connection() as connection:
            rows = connection.execute(
                "SELECT title,source,content,chunk_index FROM knowledge_chunks WHERE collection=?",
                (collection[:100],),
            ).fetchall()
        ranked = []
        for row in rows:
            haystack = (row["title"] + " " + row["content"]).casefold()
            hits = sum(1 for term in terms if term in haystack)
            if hits:
                ranked.append((hits / len(terms), row))
        ranked.sort(key=lambda item: (item[0], -int(item[1]["chunk_index"])), reverse=True)
        return [{"title": str(row["title"]), "source": str(row["source"]),
                 "content": str(row["content"])[:2500], "similarity": round(score, 4),
                 "chunk_index": row["chunk_index"]} for score, row in ranked[:max(1, min(int(limit), 8))]]
    vector = embed([query[:4000]])[0]
    rows = _request(c["db_url"] + "/rest/v1/rpc/match_saarthi_knowledge", c["db_key"],
        payload={"query_embedding": vector, "match_count": max(1, min(int(limit), 8)),
                 "filter_collection": collection[:100]}, timeout=4.0)
    if not isinstance(rows, list):
        return []
    return [{"title": str(row.get("title") or "Untitled source")[:300],
             "source": str(row.get("source") or "")[:1000], "content": str(row.get("content") or "")[:2500],
             "similarity": row.get("similarity"), "chunk_index": row.get("chunk_index")}
            for row in rows[:8] if isinstance(row, dict)]

def context_for_query(query: str, *, limit: int = 5) -> list[dict[str, Any]]:
    try:
        return search(query, limit=limit)
    except Exception:
        return []

def admin_token_valid(value: str) -> bool:
    expected = os.getenv("SAARTHI_KNOWLEDGE_ADMIN_TOKEN", "").strip()
    return bool(expected and value and hmac.compare_digest(value, expected))
