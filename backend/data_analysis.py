from __future__ import annotations

import math
import statistics
from collections import Counter
from datetime import datetime
from typing import Any

def _num(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        text = str(value).strip().replace(",", "").replace("%", "")
        if not text:
            return None
        return float(text)
    except (TypeError, ValueError):
        return None

def _is_missing(value: Any) -> bool:
    return value is None or str(value).strip().lower() in {"", "na", "n/a", "null", "none", "nan"}

def profile_dataset(columns: list[str], rows: list[dict[str, Any]]) -> dict[str, Any]:
    profiles = []
    duplicate_count = len(rows) - len({tuple(str(r.get(c, "")) for c in columns) for r in rows})
    for col in columns:
        values = [r.get(col) for r in rows]
        missing = sum(_is_missing(v) for v in values)
        nums = [n for n in (_num(v) for v in values) if n is not None]
        unique = len({str(v) for v in values if not _is_missing(v)})
        item: dict[str, Any] = {
            "column": col,
            "rows": len(rows),
            "missing": missing,
            "missing_pct": round((missing / len(rows) * 100), 2) if rows else 0,
            "unique": unique,
            "type": "numeric" if nums and len(nums) == len([v for v in values if not _is_missing(v)]) else "text",
        }
        if nums:
            item.update({
                "count": len(nums),
                "min": min(nums),
                "max": max(nums),
                "mean": statistics.fmean(nums),
                "median": statistics.median(nums),
            })
        profiles.append(item)
    return {"row_count": len(rows), "column_count": len(columns), "duplicate_rows": duplicate_count, "columns": profiles}

def _numeric_columns(columns: list[str], rows: list[dict[str, Any]]) -> list[str]:
    result = []
    for col in columns:
        vals = [r.get(col) for r in rows if not _is_missing(r.get(col))]
        nums = [_num(v) for v in vals]
        if vals and all(n is not None for n in nums):
            result.append(col)
    return result

def summarize_column(rows: list[dict[str, Any]], column: str) -> dict[str, Any]:
    nums = [n for n in (_num(r.get(column)) for r in rows) if n is not None]
    if not nums:
        counts = Counter(str(r.get(column)) for r in rows if not _is_missing(r.get(column)))
        return {"column": column, "type": "categorical", "counts": dict(counts)}
    return {
        "column": column,
        "type": "numeric",
        "count": len(nums),
        "sum": sum(nums),
        "mean": statistics.fmean(nums),
        "median": statistics.median(nums),
        "min": min(nums),
        "max": max(nums),
        "stdev": statistics.stdev(nums) if len(nums) > 1 else 0,
    }

def group_by(rows: list[dict[str, Any]], group_column: str, value_column: str, aggregation: str = "sum") -> list[dict[str, Any]]:
    groups: dict[str, list[float]] = {}
    for row in rows:
        key = str(row.get(group_column, ""))
        value = _num(row.get(value_column))
        if value is not None:
            groups.setdefault(key, []).append(value)
    out = []
    for key, vals in groups.items():
        if aggregation == "mean":
            value = statistics.fmean(vals)
        elif aggregation == "count":
            value = len(vals)
        elif aggregation == "min":
            value = min(vals)
        elif aggregation == "max":
            value = max(vals)
        else:
            value = sum(vals)
        out.append({group_column: key, value_column: value})
    return out

def percentage_change(old: Any, new: Any) -> float | None:
    a, b = _num(old), _num(new)
    if a is None or b is None or a == 0:
        return None
    return (b - a) / abs(a) * 100

def correlation(rows: list[dict[str, Any]], x_column: str, y_column: str) -> float | None:
    pairs = [(_num(r.get(x_column)), _num(r.get(y_column))) for r in rows]
    pairs = [(x, y) for x, y in pairs if x is not None and y is not None]
    if len(pairs) < 2:
        return None
    xs, ys = zip(*pairs)
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return None
    return sum((x - mx) * (y - my) for x, y in pairs) / (dx * dy)

def build_chart(rows: list[dict[str, Any]], chart_type: str, x_key: str, series_key: str, title: str) -> dict[str, Any]:
    chart_type = chart_type if chart_type in {"bar", "line", "pie", "scatter"} else "bar"
    data = [{x_key: r.get(x_key), series_key: r.get(series_key)} for r in rows]
    return {"chartType": chart_type, "title": title, "xKey": x_key, "series": [{"key": series_key, "label": series_key}], "data": data}

def analyze_dataset(columns: list[str], rows: list[dict[str, Any]]) -> dict[str, Any]:
    numeric = _numeric_columns(columns, rows)
    return {
        "profile": profile_dataset(columns, rows),
        "numeric_columns": numeric,
        "summaries": [summarize_column(rows, c) for c in numeric],
        "quality": {
            "duplicate_rows": profile_dataset(columns, rows)["duplicate_rows"],
            "missing_columns": [c for c in columns if any(_is_missing(r.get(c)) for r in rows)],
        },
    }
