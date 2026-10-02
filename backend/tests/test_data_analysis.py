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
