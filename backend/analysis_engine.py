from __future__ import annotations

import re
from typing import Any


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", str(text or "")) if len(s.strip()) >= 20]


def extract_evidence(text: str, query: str = "", limit: int = 20) -> list[dict[str, Any]]:
    sentences = _sentences(text)
    terms = re.findall(r"[a-z0-9]{3,}", query.lower())
    ranked = []
    for sentence in sentences:
        low = sentence.lower()
        overlap = sum(1 for term in terms if term in low)
        ranked.append((overlap, sentence))
    ranked.sort(key=lambda x: x[0], reverse=True)
    return [{"text": sentence, "relevance": score} for score, sentence in ranked[:limit]]


def assumptions(text: str) -> list[str]:
    patterns = [r"\b(?:assume|assuming|assumption)\b[^.?!]*", r"\b(?:likely|probably|may|might|could)\b[^.?!]*"]
    found = []
    for pattern in patterns:
        found.extend(m.group(0).strip() for m in re.finditer(pattern, text, re.I))
    return list(dict.fromkeys(found))[:15]


def risks(text: str) -> list[dict[str, Any]]:
    categories = {
        "security": ["security", "breach", "attack", "credential", "privacy"],
        "operational": ["failure", "downtime", "delay", "capacity", "dependency"],
        "financial": ["cost", "budget", "revenue", "loss", "price"],
        "compliance": ["compliance", "regulation", "legal", "audit", "policy"],
        "data": ["missing", "incomplete", "stale", "quality", "bias"],
    }
    low = text.lower()
    return [{"category": k, "signals": [x for x in v if x in low], "severity": "review"} for k, v in categories.items() if any(x in low for x in v)]


def root_cause(text: str) -> dict[str, Any]:
    causal = [s for s in _sentences(text) if re.search(r"\b(because|caused by|due to|resulted from|driven by|root cause)\b", s, re.I)]
    return {"candidate_causes": causal[:10], "method": "Extracted causal statements; not independent causal proof."}


def tradeoffs(text: str) -> list[dict[str, Any]]:
    marker = re.compile(r"\b(?:however|but|while|versus|vs\.?|trade[- ]?off|on the other hand|whereas)\b", re.I)
    return [{"statement": s} for s in _sentences(text) if marker.search(s)][:10]


def compare_items(items: list[dict[str, Any]]) -> dict[str, Any]:
    normalized = []
    for item in items:
        name = str(item.get("name") or item.get("id") or f"item_{len(normalized)+1}")
        facts = item.get("facts") if isinstance(item.get("facts"), dict) else {}
        normalized.append({"name": name, "facts": facts})
    keys = sorted({k for item in normalized for k in item["facts"]})
    return {"items": normalized, "dimensions": keys, "matrix": [{"name": x["name"], **{k: x["facts"].get(k) for k in keys}} for x in normalized]}


def analyze_text(text: str, query: str = "") -> dict[str, Any]:
    evidence = extract_evidence(text, query)
    return {
        "evidence": evidence,
        "assumptions": assumptions(text),
        "risks": risks(text),
        "root_cause": root_cause(text),
        "tradeoffs": tradeoffs(text),
        "quality": {
            "character_count": len(text),
            "sentence_count": len(_sentences(text)),
            "evidence_count": len(evidence),
            "limitation": "Structures supplied evidence; does not independently establish truth or causality.",
        },
    }
