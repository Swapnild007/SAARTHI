from __future__ import annotations

import ipaddress
import re
import socket
from html import unescape
from typing import Any
from urllib.parse import quote_plus, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener


SEARCH_ENDPOINT = "https://html.duckduckgo.com/html/?q={query}"


class _NoRedirectHandler(HTTPRedirectHandler):
    """Reject redirects so URL validation cannot be bypassed by a remote server."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("redirects are disabled for remote research sources")


_SAFE_OPENER = build_opener(_NoRedirectHandler())
MAX_SOURCE_BYTES = 1_500_000
DEFAULT_RESULTS = 5

_AUTHORITY_HINTS = {
    ".gov": 1.0,
    ".gov.uk": 1.0,
    ".edu": 0.95,
    ".ac.uk": 0.95,
    "who.int": 1.0,
    "worldbank.org": 0.95,
    "oecd.org": 0.95,
    "un.org": 0.95,
    "nih.gov": 1.0,
    "ncbi.nlm.nih.gov": 1.0,
    "nature.com": 0.9,
    "sciencedirect.com": 0.9,
    "reuters.com": 0.9,
    "apnews.com": 0.9,
}


def _clean_text(value: Any, limit: int = 12000) -> str:
    text = unescape(re.sub(r"<[^>]+>", " ", str(value or "")))
    text = re.sub(r"\\s+", " ", text).strip()
    return text[:limit]


def _keywords(query: str) -> list[str]:
    stop = {"what", "when", "where", "which", "who", "why", "how", "is", "are", "the", "and", "for", "with", "about"}
    return [x for x in re.findall(r"[a-z0-9]{3,}", query.lower()) if x not in stop][:16]


def _public_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    host = parsed.hostname.lower()
    if host in {"localhost", "localhost.localdomain"}:
        return False
    if parsed.username or parsed.password:
        return False
    if parsed.port not in {None, 80, 443}:
        return False
    try:
        addresses = socket.getaddrinfo(host, None)
        for item in addresses:
            ip = ipaddress.ip_address(item[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                return False
    except Exception:
        # DNS failures are rejected rather than treated as safe.
        return False
    return True


def _authority(url: str) -> float:
    host = (urlparse(url).hostname or "").lower()
    for hint, score in _AUTHORITY_HINTS.items():
        if host == hint or host.endswith(hint):
            return score
    if host.endswith((".org", ".edu", ".gov")):
        return 0.8
    return 0.55


def evaluate_source(source: dict[str, Any], query: str) -> dict[str, Any]:
    url = str(source.get("url") or "")
    title = _clean_text(source.get("title"), 300)
    text = _clean_text(source.get("text"), 12000)
    terms = _keywords(query)
    lowered = (title + " " + text).lower()
    overlap = sum(1 for term in terms if term in lowered)
    relevance = overlap / max(len(terms), 1)
    authority = _authority(url) if url else 0.35
    directness = 1.0 if text else 0.25
    score = round(min(1.0, authority * 0.45 + relevance * 0.4 + directness * 0.15), 3)
    reasons = []
    reasons.append("recognized authoritative domain" if authority >= 0.9 else "general web source")
    reasons.append("contains query terms" if relevance > 0 else "limited keyword overlap")
    reasons.append("has extracted source text" if text else "no extracted source text")
    return {
        **source,
        "title": title or url,
        "text": text,
        "quality": {"score": score, "authority": round(authority, 3), "relevance": round(relevance, 3), "reasons": reasons},
    }


def extract_evidence(source: dict[str, Any], query: str, limit: int = 4) -> list[dict[str, Any]]:
    terms = _keywords(query)
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\\s+", source.get("text", "")) if len(s.strip()) >= 40]
    ranked = []
    for sentence in sentences:
        lowered = sentence.lower()
        overlap = sum(1 for term in terms if term in lowered)
        if overlap:
            ranked.append((overlap, sentence))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [
        {"source_url": source.get("url"), "source_title": source.get("title"), "text": sentence}
        for _, sentence in ranked[:limit]
    ]


def _parse_search_results(html: str, limit: int) -> list[dict[str, str]]:
    pattern = re.compile(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.I | re.S)
    results = []
    for url, title in pattern.findall(html):
        clean_url = unescape(url)
        if "uddg=" in clean_url:
            match = re.search(r"[?&]uddg=([^&]+)", clean_url)
            if match:
                from urllib.parse import unquote
                clean_url = unquote(match.group(1))
        results.append({"url": clean_url, "title": _clean_text(title, 300)})
        if len(results) >= limit:
            break
    return results


def search_web(query: str, limit: int = DEFAULT_RESULTS) -> list[dict[str, str]]:
    if not query.strip():
        return []
    url = SEARCH_ENDPOINT.format(query=quote_plus(query[:500]))
    request = Request(url, headers={"User-Agent": "SAARTHI-Research/1.0"})
    with _SAFE_OPENER.open(request, timeout=12) as response:
        html = response.read().decode("utf-8", errors="replace")
    return [item for item in _parse_search_results(html, limit) if _public_url(item["url"])]


def fetch_source(url: str) -> dict[str, Any]:
    if not _public_url(url):
        raise ValueError("source URL is not a permitted public HTTP(S) URL")
    request = Request(url, headers={"User-Agent": "SAARTHI-Research/1.0"})
    with _SAFE_OPENER.open(request, timeout=15) as response:
        content_type = str(response.headers.get("Content-Type") or "")
        body = response.read(MAX_SOURCE_BYTES).decode("utf-8", errors="replace")
    return {"url": url, "title": url, "text": _clean_text(body), "content_type": content_type}


def build_research_brief(query: str, sources: list[dict[str, Any]]) -> dict[str, Any]:
    evaluated = [evaluate_source(source, query) for source in sources if source.get("url")]
    evidence = []
    for source in evaluated:
        evidence.extend(extract_evidence(source, query))
    return {
        "question": query.strip(),
        "source_count": len(evaluated),
        "sources": evaluated,
        "evidence": evidence[:20],
        "limitations": [
            "Source quality is a deterministic heuristic, not peer review.",
            "Search coverage depends on the available search index and accessible pages.",
            "Evidence excerpts are extracted from retrieved page text and should be checked against the original source.",
        ],
    }


def research(query: str, *, urls: list[str] | None = None, search: bool = True, max_sources: int = DEFAULT_RESULTS) -> dict[str, Any]:
    discovered: list[dict[str, Any]] = []
    if search:
        try:
            discovered = search_web(query, max_sources)
        except Exception as exc:
            discovered = [{"url": "", "title": "Search unavailable", "text": str(exc)}]

    candidates = list(urls or [])
    candidates.extend(item["url"] for item in discovered if item.get("url"))
    unique = []
    seen = set()
    for url in candidates:
        if url and url not in seen:
            seen.add(url)
            unique.append(url)
        if len(unique) >= max_sources:
            break

    sources = []
    for url in unique:
        try:
            sources.append(fetch_source(url))
        except Exception as exc:
            sources.append({"url": url, "title": url, "text": "", "fetch_error": str(exc)[:240]})

    return build_research_brief(query, sources)
