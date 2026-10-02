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


def _date_like(value: Any) -> bool:
    if _is_missing(value):
        return False
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%Y/%m/%d", "%b %Y", "%B %Y"):
        try:
            datetime.strptime(text, fmt)
            return True
        except ValueError:
            continue
    return False


def _column_roles(columns: list[str], rows: list[dict[str, Any]]) -> dict[str, list[str]]:
    numeric, categorical, temporal = [], [], []
    for col in columns:
        values = [r.get(col) for r in rows if not _is_missing(r.get(col))]
        if not values:
            categorical.append(col)
            continue
        if all(_num(v) is not None for v in values):
            numeric.append(col)
        elif sum(_date_like(v) for v in values) / len(values) >= 0.8:
            temporal.append(col)
        else:
            categorical.append(col)
    return {"numeric": numeric, "categorical": categorical, "temporal": temporal}


def recommend_visuals(columns: list[str], rows: list[dict[str, Any]], *, limit: int = 4) -> list[dict[str, Any]]:
    """Choose useful visual forms from the supplied data shape.

    This function only uses supplied rows and deterministic rules. It never
    creates values and is intentionally conservative about pie charts.
    """
    if not rows or len(columns) < 2:
        return []
    roles = _column_roles(columns, rows)
    numeric, categorical, temporal = roles["numeric"], roles["categorical"], roles["temporal"]
    specs: list[dict[str, Any]] = []

    if temporal and numeric:
        specs.append(build_chart(rows, "line", temporal[0], numeric[0], f"{numeric[0]} over {temporal[0]}"))

    if categorical and numeric:
        group = categorical[0]
        value = numeric[0]
        grouped = group_by(rows, group, value, "sum")
        grouped.sort(key=lambda item: float(item.get(value) or 0), reverse=True)
        specs.append(build_chart(grouped[:12], "bar", group, value, f"{value} by {group}"))
        if len(grouped) <= 6:
            specs.append(build_chart(grouped, "pie", group, value, f"{value} share by {group}"))

    if len(numeric) >= 2:
        x_key, y_key = numeric[:2]
        specs.append(build_chart(rows[:5000], "scatter", x_key, y_key, f"{y_key} vs {x_key}"))

    if len(categorical) >= 2 and numeric:
        row_key, col_key, value_key = categorical[0], categorical[1], numeric[0]
        row_values = list(dict.fromkeys(str(r.get(row_key)) for r in rows if not _is_missing(r.get(row_key))))[:12]
        col_values = list(dict.fromkeys(str(r.get(col_key)) for r in rows if not _is_missing(r.get(col_key))))[:12]
        matrix = []
        for rv in row_values:
            row = []
            for cv in col_values:
                vals = [_num(r.get(value_key)) for r in rows if str(r.get(row_key)) == rv and str(r.get(col_key)) == cv]
                vals = [v for v in vals if v is not None]
                row.append(round(statistics.fmean(vals), 4) if vals else None)
            matrix.append({"row": rv, "values": row})
        if row_values and col_values:
            specs.append({
                "chartType": "heatmap",
                "meta": {"title": f"{value_key} by {row_key} and {col_key}"},
                "rowLabels": row_values,
                "colLabels": col_values,
                "data": matrix,
            })

    unique = []
    seen = set()
    for spec in specs:
        key = (spec.get("chartType"), (spec.get("meta") or {}).get("title"))
        if key not in seen:
            seen.add(key)
            unique.append(spec)
    return unique[:max(1, limit)]
