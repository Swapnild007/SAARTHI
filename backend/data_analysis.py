from __future__ import annotations

import math
import statistics
from collections import Counter
from datetime import datetime, timedelta
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

SUPPORTED_CHART_TYPES = {
    "bar", "line", "pie", "donut", "scatter", "bubble", "area",
    "stacked_bar", "histogram", "box", "radar", "funnel", "gauge",
    "waterfall", "heatmap",
}

def build_chart(rows: list[dict[str, Any]], chart_type: str, x_key: str, series_key: str, title: str) -> dict[str, Any]:
    """Build a renderer-ready visualization spec using only supplied data."""
    chart_type = chart_type if chart_type in SUPPORTED_CHART_TYPES else "bar"
    if chart_type in {"pie", "donut"}:
        data = [{x_key: r.get(x_key), series_key: r.get(series_key)} for r in rows if _num(r.get(series_key)) is not None]
        return {
            "chartType": chart_type,
            "meta": {"title": title},
            "nameKey": x_key,
            "valueKey": series_key,
            "data": data,
        }

    if chart_type in {"scatter", "bubble"}:
        data = [{x_key: _num(r.get(x_key)), series_key: _num(r.get(series_key))} for r in rows]
        data = [r for r in data if r[x_key] is not None and r[series_key] is not None]
        return {
            "chartType": chart_type,
            "meta": {"title": title},
            "xKey": x_key,
            "series": [{"dataKey": series_key, "label": series_key}],
            "sizeKey": series_key if chart_type == "bubble" else None,
            "data": data,
        }

    if chart_type == "histogram":
        values = [n for n in (_num(r.get(series_key)) for r in rows) if n is not None]
        if not values:
            return {"chartType": "histogram", "meta": {"title": title}, "xKey": "bin", "series": [], "data": []}
        bins = min(10, max(4, int(math.sqrt(len(values)))))
        lo, hi = min(values), max(values)
        width = (hi - lo) / bins if hi != lo else 1.0
        counts = [0] * bins
        for value in values:
            index = min(bins - 1, max(0, int((value - lo) / width)))
            counts[index] += 1
        data = [
            {"bin": f"{lo + i * width:.2f}–{lo + (i + 1) * width:.2f}", "count": counts[i]}
            for i in range(bins)
        ]
        return {"chartType": "histogram", "meta": {"title": title}, "xKey": "bin",
                "series": [{"dataKey": "count", "label": "Count"}], "data": data}

    if chart_type == "box":
        groups: dict[str, list[float]] = {}
        for row in rows:
            value = _num(row.get(series_key))
            if value is not None:
                groups.setdefault(str(row.get(x_key, "")), []).append(value)
        return {
            "chartType": "box",
            "meta": {"title": title},
            "groups": [groups[key] for key in groups],
            "groupLabels": list(groups),
            "data": [{"category": key, "value": vals} for key, vals in groups.items()],
        }

    if chart_type == "funnel":
        data = [{x_key: str(r.get(x_key, "")), series_key: _num(r.get(series_key))} for r in rows]
        data = [r for r in data if r[series_key] is not None]
        return {
            "chartType": "funnel",
            "meta": {"title": title},
            "nameKey": x_key,
            "valueKey": series_key,
            "data": data,
        }

    if chart_type == "gauge":
        values = [n for n in (_num(r.get(series_key)) for r in rows) if n is not None]
        actual = values[0] if values else 0.0
        scale_max = max(values) if values else 100.0
        return {
            "chartType": "gauge",
            "meta": {"title": title, "target_type": "display_scale_max", "not_a_business_target": True},
            "data": [{"value": actual, "target": scale_max}],
        }

    if chart_type == "radar":
        data = [{x_key: str(r.get(x_key, "")), series_key: _num(r.get(series_key))} for r in rows]
        data = [r for r in data if r[series_key] is not None]
        return {
            "chartType": "radar",
            "meta": {"title": title},
            "xKey": x_key,
            "series": [{"dataKey": series_key, "label": series_key}],
            "data": data,
        }

    if chart_type == "waterfall":
        data = [{"category": str(r.get(x_key, "")), "value": _num(r.get(series_key))} for r in rows]
        data = [r for r in data if r["value"] is not None]
        return {"chartType": "waterfall", "meta": {"title": title}, "data": data}

    data = [{x_key: r.get(x_key), series_key: _num(r.get(series_key))} for r in rows]
    data = [r for r in data if r[series_key] is not None]
    return {
        "chartType": chart_type,
        "meta": {"title": title},
        "xKey": x_key,
        "series": [{"dataKey": series_key, "label": series_key}],
        "data": data,
    }


def clean_dataset(
    columns: list[str],
    rows: list[dict[str, Any]],
    *,
    drop_duplicate_rows: bool = True,
    trim_text: bool = True,
) -> dict[str, Any]:
    """Deterministically clean a dataset without inventing business values.

    Missing values are reported, not silently imputed. Text is normalized and
    duplicate rows can be removed. The original input is never mutated.
    """
    cleaned: list[dict[str, Any]] = []
    seen: set[tuple[str, ...]] = set()
    duplicates_removed = 0
    text_normalized = 0

    for source in rows:
        row = {c: source.get(c) for c in columns}
        if trim_text:
            for c, value in list(row.items()):
                if isinstance(value, str):
                    normalized = value.strip()
                    if normalized != value:
                        text_normalized += 1
                    row[c] = normalized
        key = tuple("" if _is_missing(row.get(c)) else str(row.get(c)) for c in columns)
        if drop_duplicate_rows and key in seen:
            duplicates_removed += 1
            continue
        seen.add(key)
        cleaned.append(row)

    missing_by_column = {
        c: sum(_is_missing(row.get(c)) for row in cleaned)
        for c in columns
    }
    return {
        "rows": cleaned,
        "row_count": len(cleaned),
        "duplicates_removed": duplicates_removed,
        "text_values_normalized": text_normalized,
        "missing_by_column": missing_by_column,
        "missing_policy": "reported_only",
    }


def descriptive_statistics(values: list[Any]) -> dict[str, Any]:
    nums = [n for n in (_num(v) for v in values) if n is not None]
    if not nums:
        return {"count": 0}
    ordered = sorted(nums)
    q = lambda p: ordered[min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * p))))]
    mean = statistics.fmean(nums)
    stdev = statistics.stdev(nums) if len(nums) > 1 else 0.0
    variance = statistics.variance(nums) if len(nums) > 1 else 0.0
    return {
        "count": len(nums),
        "sum": sum(nums),
        "mean": mean,
        "median": statistics.median(nums),
        "min": min(nums),
        "max": max(nums),
        "range": max(nums) - min(nums),
        "stdev": stdev,
        "variance": variance,
        "q1": q(0.25),
        "q3": q(0.75),
        "iqr": q(0.75) - q(0.25),
    }


def detect_outliers(values: list[Any]) -> dict[str, Any]:
    nums = [n for n in (_num(v) for v in values) if n is not None]
    if len(nums) < 4:
        return {"method": "iqr", "count": 0, "values": []}
    stats = descriptive_statistics(nums)
    lower = stats["q1"] - 1.5 * stats["iqr"]
    upper = stats["q3"] + 1.5 * stats["iqr"]
    outliers = [v for v in nums if v < lower or v > upper]
    return {"method": "iqr", "lower_bound": lower, "upper_bound": upper, "count": len(outliers), "values": outliers[:100]}


def linear_forecast(values: list[Any], periods: int = 3) -> dict[str, Any]:
    """Deterministic trend forecast with residual uncertainty diagnostics."""
    nums = [n for n in (_num(v) for v in values) if n is not None]
    periods = max(1, min(int(periods), 24))
    n = len(nums)
    if n < 3:
        return {"method": "linear_trend", "status": "insufficient_history", "forecast": [], "history_count": n}
    xs = list(range(n))
    mx, my = statistics.fmean(xs), statistics.fmean(nums)
    denom = sum((x - mx) ** 2 for x in xs)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, nums)) / denom if denom else 0.0
    intercept = my - slope * mx
    fitted = [intercept + slope * x for x in xs]
    residuals = [y - f for y, f in zip(nums, fitted)]
    ss_res = sum(r * r for r in residuals)
    ss_tot = sum((y - my) ** 2 for y in nums)
    r2 = 1 - ss_res / ss_tot if ss_tot else 1.0
    residual_se = math.sqrt(ss_res / max(1, n - 2))
    forecast = []
    for i in range(periods):
        point = intercept + slope * (n + i)
        margin = 1.96 * residual_se * math.sqrt(1 + 1 / n + ((n + i) - mx) ** 2 / max(denom, 1))
        forecast.append({"period_index": n + i + 1, "value": point, "lower_95": point - margin, "upper_95": point + margin})
    return {
        "method": "linear_trend",
        "status": "ok",
        "history_count": n,
        "slope": slope,
        "intercept": intercept,
        "r2": max(-1.0, min(1.0, r2)),
        "residual_standard_error": residual_se,
        "forecast": forecast,
        "limitations": ["trend extrapolation only", "no causal model", "seasonality not independently modeled"],
    }


def time_series_analysis(rows: list[dict[str, Any]], date_column: str, value_column: str, forecast_periods: int = 3) -> dict[str, Any]:
    points = []
    for row in rows:
        raw_date = row.get(date_column)
        value = _num(row.get(value_column))
        if value is None or _is_missing(raw_date):
            continue
        text = str(raw_date).strip()
        parsed = None
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%Y/%m/%d", "%b %Y", "%B %Y"):
            try:
                parsed = datetime.strptime(text, fmt)
                break
            except ValueError:
                continue
        if parsed is not None:
            points.append((parsed, value))
    points.sort(key=lambda item: item[0])
    values = [v for _, v in points]
    changes = [percentage_change(values[i - 1], values[i]) for i in range(1, len(values))]
    return {
        "date_column": date_column,
        "value_column": value_column,
        "observations": len(points),
        "start": points[0][0].isoformat() if points else None,
        "end": points[-1][0].isoformat() if points else None,
        "period_changes_pct": changes,
        "trend": linear_forecast(values, forecast_periods),
        "seasonality": {"status": "not_estimated", "reason": "baseline engine requires more periodic history"},
    }


def infer_kpi_aggregation(column: str) -> str:
    name = str(column).lower()
    if any(token in name for token in ("rate", "pct", "percent", "margin", "aht", "asa", "csat", "average", "avg", "score")):
        return "mean"
    if any(token in name for token in ("count", "volume", "sales", "revenue", "cost", "orders", "units", "calls", "handled", "abandon", "throughput")):
        return "sum"
    return "mean"


def infer_kpi_direction(column: str) -> str:
    name = str(column).lower()
    return "lower_is_better" if any(token in name for token in (
        "cost", "error", "defect", "downtime", "wait", "aht", "asa", "abandon", "turnover", "incident"
    )) else "higher_is_better"


def aggregate_values(values: list[Any], aggregation: str) -> float | None:
    nums = [n for n in (_num(v) for v in values) if n is not None]
    if not nums:
        return None
    if aggregation == "sum":
        return sum(nums)
    if aggregation == "min":
        return min(nums)
    if aggregation == "max":
        return max(nums)
    return statistics.fmean(nums)


def kpi_analysis(rows: list[dict[str, Any]], value_column: str, target_column: str | None = None, direction: str | None = None) -> dict[str, Any]:
    aggregation = infer_kpi_aggregation(value_column)
    actual = aggregate_values([r.get(value_column) for r in rows], aggregation)
    if actual is None:
        return {"status": "no_numeric_actuals", "value_column": value_column}
    direction = direction or infer_kpi_direction(value_column)
    result: dict[str, Any] = {
        "status": "ok",
        "metric": value_column,
        "actual": actual,
        "count": sum(_num(r.get(value_column)) is not None for r in rows),
        "aggregation": aggregation,
        "direction": direction,
    }
    if target_column:
        target = aggregate_values([r.get(target_column) for r in rows], aggregation)
        if target is not None:
            variance = actual - target
            variance_pct = (variance / abs(target) * 100) if target else None
            meets = variance >= 0 if direction == "higher_is_better" else variance <= 0
            result.update({
                "target": target,
                "variance": variance,
                "variance_pct": variance_pct,
                "status_vs_target": "meets_target" if meets else "below_target",
            })
    return result


def analytical_calculations(columns: list[str], rows: list[dict[str, Any]]) -> dict[str, Any]:
    numeric = _numeric_columns(columns, rows)
    summaries = {c: descriptive_statistics([r.get(c) for r in rows]) for c in numeric}
    outliers = {c: detect_outliers([r.get(c) for r in rows]) for c in numeric}
    correlations = {}
    for i, x in enumerate(numeric):
        for y in numeric[i + 1:]:
            correlations[f"{x}__{y}"] = correlation(rows, x, y)
    rankings = {}
    for c in numeric:
        valid = [(str(r.get(c)), _num(r.get(c))) for r in rows]
        rankings[c] = [{"label": label, "value": value} for label, value in sorted(
            [(label, value) for label, value in valid if value is not None],
            key=lambda item: item[1], reverse=True
        )[:10]]
    return {
        "numeric_columns": numeric,
        "descriptive_statistics": summaries,
        "outliers": outliers,
        "correlations": correlations,
        "rankings": rankings,
    }

def build_findings(analysis: dict[str, Any]) -> list[dict[str, Any]]:
    """Create deterministic, traceable findings from computed metrics."""
    findings: list[dict[str, Any]] = []
    calculations = analysis.get("calculations", {})
    for column, stats in calculations.get("descriptive_statistics", {}).items():
        if stats.get("count", 0):
            findings.append({
                "type": "descriptive",
                "metric": column,
                "statement": f"{column}: mean {stats['mean']:.4g}, median {stats['median']:.4g}, range {stats['min']:.4g} to {stats['max']:.4g}.",
                "source": f"calculations.descriptive_statistics.{column}",
            })
    for column, info in calculations.get("outliers", {}).items():
        if info.get("count", 0):
            findings.append({
                "type": "outlier",
                "metric": column,
                "statement": f"{column}: {info['count']} IQR outlier(s) detected.",
                "source": f"calculations.outliers.{column}",
            })
    for metric in analysis.get("kpis", []):
        if metric.get("target") is not None:
            findings.append({
                "type": "kpi",
                "metric": metric["metric"],
                "statement": f"{metric['metric']}: actual {metric['actual']:.4g} vs target {metric['target']:.4g}; {metric['status_vs_target']}.",
                "source": f"kpis.{metric['metric']}",
            })
    for column, forecast in analysis.get("forecasts", {}).items():
        trend = forecast.get("trend", {})
        if trend.get("status") == "ok":
            findings.append({
                "type": "forecast",
                "metric": column,
                "statement": f"{column}: linear trend slope {trend['slope']:.4g}, R² {trend['r2']:.3f}. Forecast is trend-based, not causal.",
                "source": f"forecasts.{column}.trend",
            })
    return findings

def analyze_dataset(columns: list[str], rows: list[dict[str, Any]]) -> dict[str, Any]:
    cleaned = clean_dataset(columns, rows)
    clean_rows = cleaned["rows"]
    profile = profile_dataset(columns, rows)
    roles = _column_roles(columns, clean_rows)
    calculations = analytical_calculations(columns, clean_rows)

    forecasts = {}
    temporal = roles["temporal"]
    numeric = roles["numeric"]
    if temporal and numeric:
        forecasts[numeric[0]] = time_series_analysis(clean_rows, temporal[0], numeric[0])

    kpis = []
    lower = {c.lower(): c for c in columns}
    for value_col in numeric:
        target_col = next((lower[name] for name in (
            f"{value_col.lower()} target", f"target {value_col.lower()}",
            f"{value_col.lower()}_target", "target"
        ) if name in lower and lower[name] != value_col), None)
        kpis.append(kpi_analysis(clean_rows, value_col, target_col))

    analyzed_rows = len(clean_rows)
    source_rows = len(rows)
    coverage_pct = (analyzed_rows / source_rows * 100) if source_rows else 0.0
    return {
        "profile": profile,
        "numeric_columns": numeric,
        "column_roles": roles,
        "coverage": {
            "source_rows_received": source_rows,
            "rows_analyzed": analyzed_rows,
            "coverage_pct": round(coverage_pct, 2),
            "bounded": source_rows > analyzed_rows,
        },
        "summaries": [summarize_column(clean_rows, c) for c in numeric],
        "calculations": calculations,
        "forecasts": forecasts,
        "kpis": kpis,
        "findings": build_findings({
            "calculations": calculations,
            "kpis": kpis,
            "forecasts": forecasts,
        }),
        "cleaning": cleaned,
        "quality": {
            "duplicate_rows": profile["duplicate_rows"],
            "missing_columns": [c for c in columns if any(_is_missing(r.get(c)) for r in rows)],
            "missing_policy": "reported_only",
            "outlier_columns": [c for c, info in calculations["outliers"].items() if info["count"] > 0],
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
