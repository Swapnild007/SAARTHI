from backend.data_analysis import build_chart, recommend_visuals

CHART_TYPES = [
    "bar", "line", "pie", "donut", "scatter", "bubble", "area",
    "stacked_bar", "histogram", "box", "radar", "funnel", "gauge",
    "waterfall", "heatmap",
]

def test_all_chart_types_are_accepted():
    rows = [
        {"category": "A", "value": 10},
        {"category": "B", "value": 20},
        {"category": "C", "value": 30},
    ]
    for chart_type in CHART_TYPES:
        spec = build_chart(rows, chart_type, "category", "value", f"Test {chart_type}")
        assert spec["chartType"] == chart_type
        assert spec["data"]

def test_visual_recommendation_uses_supplied_data_only():
    rows = [
        {"date": "2026-01-01", "region": "North", "channel": "Online", "sales": 100, "orders": 10},
        {"date": "2026-02-01", "region": "South", "channel": "Retail", "sales": 150, "orders": 15},
        {"date": "2026-03-01", "region": "North", "channel": "Online", "sales": 125, "orders": 12},
    ]
    specs = recommend_visuals(list(rows[0]), rows, limit=10)
    assert specs
    serialized = str(specs)
    assert "999999" not in serialized
    assert "100" in serialized
    assert "150" in serialized


from backend.data_analysis import (
    clean_dataset,
    descriptive_statistics,
    detect_outliers,
    linear_forecast,
    kpi_analysis,
    time_series_analysis,
)

def test_cleaning_reports_duplicates_and_missing_without_inventing_values():
    rows = [
        {"name": " A ", "sales": "100"},
        {"name": "A", "sales": "100"},
        {"name": "B", "sales": None},
    ]
    result = clean_dataset(["name", "sales"], rows)
    assert result["duplicates_removed"] == 1
    assert result["missing_by_column"]["sales"] == 1
    assert result["rows"][0]["name"] == "A"
    assert result["rows"][0]["sales"] == "100"

def test_statistics_and_outliers_are_deterministic():
    stats = descriptive_statistics([1, 2, 3, 4, 100])
    assert stats["count"] == 5
    assert stats["median"] == 3
    assert detect_outliers([1, 2, 3, 4, 100])["count"] == 1

def test_forecast_has_fit_diagnostics_and_interval():
    result = linear_forecast([10, 12, 14, 16, 18], periods=2)
    assert result["status"] == "ok"
    assert len(result["forecast"]) == 2
    assert result["forecast"][0]["lower_95"] <= result["forecast"][0]["value"] <= result["forecast"][0]["upper_95"]
    assert result["r2"] > 0.9

def test_kpi_direction_and_target_variance():
    rows = [
        {"cost": 90, "target": 100},
        {"cost": 80, "target": 100},
    ]
    result = kpi_analysis(rows, "cost", "target")
    assert result["aggregation"] == "sum"
    assert result["direction"] == "lower_is_better"
    assert result["status_vs_target"] == "below_target"

def test_time_series_analysis_orders_dates_and_forecasts():
    rows = [
        {"month": "2026-03-01", "revenue": 130},
        {"month": "2026-01-01", "revenue": 100},
        {"month": "2026-02-01", "revenue": 115},
    ]
    result = time_series_analysis(rows, "month", "revenue", forecast_periods=1)
    assert result["observations"] == 3
    assert result["start"].startswith("2026-01")
    assert result["trend"]["status"] == "ok"


def test_specialized_chart_specs_are_structured_for_renderer():
    rows = [
        {"category": "A", "value": 10},
        {"category": "B", "value": 20},
        {"category": "C", "value": 30},
        {"category": "D", "value": 40},
    ]
    histogram = build_chart(rows, "histogram", "category", "value", "Histogram")
    assert histogram["series"][0]["dataKey"] == "count"
    assert sum(row["count"] for row in histogram["data"]) == 4

    box = build_chart(rows, "box", "category", "value", "Box")
    assert len(box["groups"]) == 4
    assert box["groupLabels"] == ["A", "B", "C", "D"]

    funnel = build_chart(rows, "funnel", "category", "value", "Funnel")
    assert funnel["nameKey"] == "category"
    assert funnel["valueKey"] == "value"

    gauge = build_chart(rows, "gauge", "category", "value", "Gauge")
    assert gauge["meta"]["not_a_business_target"] is True

    waterfall = build_chart(rows, "waterfall", "category", "value", "Waterfall")
    assert [row["value"] for row in waterfall["data"]] == [10, 20, 30, 40]

def test_kpi_target_uses_same_aggregation_as_metric():
    rows = [{"cost": 90, "target": 100}, {"cost": 80, "target": 100}]
    result = kpi_analysis(rows, "cost", "target")
    assert result["actual"] == 170
    assert result["target"] == 200
    assert result["status_vs_target"] == "meets_target"
