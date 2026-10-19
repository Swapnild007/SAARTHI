#!/usr/bin/env python3
"""Validate and project REA's raw output into a small, typed evidence contract.

This intentionally performs no code execution and treats all analyzer output as
untrusted data. It retains provenance and coverage limitations so downstream
planning cannot mistake static observations for runtime truth.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "saarthi.rea-evidence.v1"
MAX_LIMITATIONS = 100


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _safe_source(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    # Keep repository-relative source locations only; never persist runner paths.
    normalized = value.replace("\\", "/")
    if normalized.startswith("/") or "/work/" in normalized or "/runner/" in normalized:
        return normalized.rsplit("/", 1)[-1]
    return normalized[:500]


def _location(evidence: Any) -> dict[str, Any] | None:
    ev = _mapping(evidence)
    loc = _mapping(ev.get("location"))
    value = _mapping(loc.get("value"))
    start = _mapping(value.get("start"))
    end = _mapping(value.get("end"))
    source = _safe_source(value.get("source"))
    if not source and not start and not end:
        return None
    result: dict[str, Any] = {}
    if source:
        result["source"] = source
    if isinstance(start.get("line"), int):
        result["start_line"] = start["line"]
    if isinstance(start.get("column"), int):
        result["start_column"] = start["column"]
    if isinstance(end.get("line"), int):
        result["end_line"] = end["line"]
    if isinstance(end.get("column"), int):
        result["end_column"] = end["column"]
    return result or None


def normalize(raw: Any) -> dict[str, Any]:
    root = _mapping(raw)
    normalized = _mapping(root.get("normalized_result"))
    graph = _mapping(normalized.get("graph"))
    semantic = _mapping(normalized.get("semantic_graph"))
    stats = _mapping(normalized.get("statistics"))
    subject = _mapping(root.get("subject"))
    digest = _mapping(subject.get("digest"))
    provider = _mapping(root.get("provider"))
    summary = _mapping(normalized.get("summary"))

    if not isinstance(root.get("evidence_id"), str):
        raise ValueError("REA report is missing evidence_id")
    if not isinstance(digest.get("sha256"), str):
        raise ValueError("REA report is missing the analyzed subject digest")
    if not isinstance(graph.get("nodes"), list) or not isinstance(graph.get("edges"), list):
        raise ValueError("REA report is missing graph nodes or edges")

    observations: list[dict[str, Any]] = []
    for node in graph["nodes"]:
        node = _mapping(node)
        identity = _mapping(node.get("identity"))
        for observation in _list(node.get("observations")):
            observation = _mapping(observation)
            props = _mapping(observation.get("properties"))
            evidence = _mapping(observation.get("evidence"))
            item: dict[str, Any] = {
                "kind": str(node.get("kind", "unknown"))[:100],
                "label": str(observation.get("label", "observation"))[:120],
                "state": str(evidence.get("state", "unknown"))[:40],
                "confidence": str(evidence.get("confidence", "unknown"))[:40],
            }
            namespace = identity.get("namespace")
            key = identity.get("key")
            if isinstance(namespace, str):
                item["namespace"] = namespace[:120]
            if isinstance(key, str):
                item["key"] = key[:240]
            if props:
                # Keep scalar metadata only; nested analyzer payloads stay out.
                safe_props = {
                    str(k)[:100]: v
                    for k, v in props.items()
                    if isinstance(v, (str, int, float, bool)) or v is None
                }
                if safe_props:
                    item["properties"] = safe_props
            location = _location(evidence)
            if location:
                item["location"] = location
            if isinstance(observation.get("observation_id"), str):
                item["observation_id"] = observation["observation_id"][:160]
            observations.append(item)

    relationships: list[dict[str, Any]] = []
    for edge in graph["edges"]:
        edge = _mapping(edge)
        evidence = _mapping(edge.get("evidence"))
        item = {
            "relation": str(edge.get("relation", "unknown"))[:120],
            "state": str(evidence.get("state", "unknown"))[:40],
            "confidence": str(evidence.get("confidence", "unknown"))[:40],
        }
        for field in ("source_node_id", "target_node_id", "edge_id"):
            if isinstance(edge.get(field), str):
                item[field] = edge[field][:180]
        props = _mapping(edge.get("properties"))
        safe_props = {
            str(k)[:100]: v
            for k, v in props.items()
            if isinstance(v, (str, int, float, bool)) or v is None
        }
        if safe_props:
            item["properties"] = safe_props
        location = _location(evidence)
        if location:
            item["location"] = location
        relationships.append(item)

    limitations = []
    for item in _list(normalized.get("limitations")) + _list(graph.get("limitations")):
        if isinstance(item, str) and item not in limitations:
            limitations.append(item[:1000])
        if len(limitations) >= MAX_LIMITATIONS:
            break

    coverage = _mapping(graph.get("coverage"))
    semantic_coverage = _mapping(semantic.get("coverage"))
    return {
        "schema_version": SCHEMA_VERSION,
        "evidence_id": root["evidence_id"],
        "subject": {
            "name": str(subject.get("name", "unknown"))[:120],
            "sha256": digest["sha256"],
            "scope": "appforge/",
        },
        "provider": {
            "id": str(provider.get("id", "unknown"))[:120],
            "version": str(provider.get("version", "unknown"))[:40],
        },
        "analysis": {
            "operation": str(root.get("operation", "unknown"))[:120],
            "confidence": str(root.get("confidence", "unknown"))[:40],
            "authority": str(root.get("authority", "unknown"))[:80],
            "integrity_contradictions": len(_list(normalized.get("integrity_contradictions"))),
        },
        "coverage": {
            "relevant_files": int(stats.get("relevant_files", 0) or 0),
            "parsed_javascript_files": int(stats.get("parsed_javascript_files", 0) or 0),
            "parse_failures": int(stats.get("parse_failures", 0) or 0),
            "findings": int(stats.get("findings", 0) or 0),
            "graph_status": str(coverage.get("status", "unknown"))[:40],
            "graph_nodes": len(graph["nodes"]),
            "graph_relationships": len(graph["edges"]),
            "semantic_nodes": len(_list(semantic.get("nodes"))),
            "semantic_relationships": len(_list(semantic.get("relations"))),
            "semantic_unknowns": len(_list(semantic.get("unknowns"))),
            "semantic_coverage_status": str(semantic_coverage.get("status", "unknown"))[:40],
            "truncated": bool(coverage.get("truncated", False) or semantic_coverage.get("truncated", False)),
        },
        "summary": {
            "local_storage_observations": sum(1 for item in observations if item.get("namespace") == "local-storage"),
            "observations": len(observations),
            "relationships": len(relationships),
            "browser_windows": int(summary.get("browser_windows", 0) or 0),
            "ipc_operations": int(_mapping(summary.get("ipc")).get("operations", 0) or 0),
        },
        "observations": observations,
        "relationships": relationships,
        "limitations": limitations,
        "policy": {
            "static_analysis_only": True,
            "runtime_behavior_proven": False,
            "safe_for_model_instructions": False,
            "requires_human_review": True,
        },
    }


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: normalize_rea_evidence.py RAW_REPORT.json OUTPUT.json", file=sys.stderr)
        return 2
    source, destination = map(Path, argv[1:])
    try:
        raw = json.loads(source.read_text(encoding="utf-8"))
        result = normalize(raw)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"REA evidence validation failed: {exc}", file=sys.stderr)
        return 1
    print(
        "Validated REA evidence: "
        f"{result['coverage']['graph_nodes']} nodes, "
        f"{result['coverage']['graph_relationships']} relationships, "
        f"{result['coverage']['parse_failures']} parse failures"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
