from backend.analysis_engine import analyze_text, compare_items


def test_analysis_extracts_evidence_and_assumptions():
    text = "Revenue increased because demand rose. This may continue if capacity improves. Cost remains a risk."
    result = analyze_text(text, "revenue demand")
    assert result["evidence"]
    assert result["assumptions"]
    assert result["risks"]


def test_analysis_separates_candidate_root_causes():
    result = analyze_text("The outage was caused by a database failure.")
    assert result["root_cause"]["candidate_causes"]


def test_analysis_extracts_tradeoffs():
    result = analyze_text("Option A is cheaper, but Option B has lower operational risk.")
    assert result["tradeoffs"]


def test_comparison_matrix_is_structured():
    result = compare_items([
        {"name": "A", "facts": {"cost": 10, "speed": 8}},
        {"name": "B", "facts": {"cost": 12, "speed": 9}},
    ])
    assert result["dimensions"] == ["cost", "speed"]
    assert result["matrix"][0]["cost"] == 10


def test_analyze_agent_returns_deterministic_brief():
    from backend.engine import SaarthiEngine
    engine = SaarthiEngine()
    engine.cloud.generate = lambda **kwargs: ("analysis response", None)
    result = engine.run(
        message="analyze this situation",
        assistant="analyze",
        context={"analysis_text": "The system failed because capacity was exceeded. This may happen again."},
    )
    assert result["execution"] == "completed"
    brief = result["tool_results"]["analysis.brief"]
    assert brief["root_cause"]["candidate_causes"]
    assert brief["assumptions"]


def test_data_analysis_uses_full_bounded_dataset():
    from backend.data_analysis import analyze_dataset
    rows = [{"region": "North", "sales": 100}, {"region": "South", "sales": 200}, {"region": "East", "sales": 300}]
    result = analyze_dataset(["region", "sales"], rows)
    assert result["profile"]["row_count"] == 3
    assert result["summaries"][0]["sum"] == 600
    assert result["summaries"][0]["max"] == 300


def test_data_analysis_quality_detects_duplicates_and_missing_values():
    from backend.data_analysis import analyze_dataset
    rows = [
        {"region": "North", "sales": 100},
        {"region": "North", "sales": 100},
        {"region": "", "sales": 200},
    ]
    result = analyze_dataset(["region", "sales"], rows)
    assert result["quality"]["duplicate_rows"] == 1
    assert "region" in result["quality"]["missing_columns"]


def test_visual_recommendations_use_dataset_shape():
    from backend.data_analysis import recommend_visuals
    rows = [
        {"month": "2026-01-01", "region": "North", "sales": 100},
        {"month": "2026-02-01", "region": "South", "sales": 140},
        {"month": "2026-03-01", "region": "North", "sales": 180},
    ]
    specs = recommend_visuals(["month", "region", "sales"], rows)
    assert specs
    assert all(spec["chartType"] in {"bar", "line", "pie", "scatter", "heatmap"} for spec in specs)
    assert all(spec.get("data") for spec in specs)