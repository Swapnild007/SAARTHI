from backend.data_analysis import (
    validate_dataset,
    missing_value_plan,
    apply_missing_strategy,
    advanced_statistics,
    weighted_rate,
    discover_weighted_kpis,
    select_forecast_method,
    forecast_time_series,
)


def test_validation_surfaces_quality_problems():
    rows = [
        {"region": " North ", "sales": "100", "date": "2026-01-01"},
        {"region": "North", "sales": "bad", "date": "2026-02-01"},
        {"region": "North", "sales": None, "date": "not-a-date"},
    ]
    result = validate_dataset(["region", "sales", "date"], rows)
    assert result["status"] == "review_required"
    assert result["quality_score"] < 100
    assert any(x["type"] == "mixed_type" for x in result["warnings"])


def test_missing_strategy_is_explicit_and_non_mutating():
    rows = [{"x": 10}, {"x": None}, {"x": 30}]
    plan = missing_value_plan(["x"], rows)
    assert plan[0]["strategy"] == "mean"
    result = apply_missing_strategy(["x"], rows, "median")
    assert result["applied"] is True
    assert result["values_filled"] == 1
    assert rows[1]["x"] is None


def test_weighted_rate_is_not_an_average_of_percentages():
    assert weighted_rate([1, 99], [1, 999]) == 100 / 1000
    rows = [
        {"conversions": 1, "visits": 1},
        {"conversions": 99, "visits": 999},
    ]
    result = discover_weighted_kpis(rows, ["conversions", "visits"])
    assert result[0]["actual"] == 0.1


def test_advanced_statistics_expose_uncertainty():
    result = advanced_statistics(["x"], [{"x": 1}, {"x": 2}, {"x": 3}, {"x": 4}, {"x": 5}])
    assert "x" in result
    assert result["x"]["mean_ci_95"]["status"] == "ok"
    assert result["x"]["coefficient_of_variation_pct"] > 0


def test_forecast_model_selection_and_time_series():
    rows = [
        {"month": "2026-01-01", "volume": 100},
        {"month": "2026-02-01", "volume": 110},
        {"month": "2026-03-01", "volume": 120},
        {"month": "2026-04-01", "volume": 130},
        {"month": "2026-05-01", "volume": 140},
        {"month": "2026-06-01", "volume": 150},
        {"month": "2026-07-01", "volume": 160},
        {"month": "2026-08-01", "volume": 170},
    ]
    selection = select_forecast_method([r["volume"] for r in rows])
    assert selection["status"] == "backtest_selected"
    result = forecast_time_series(rows, "month", "volume", forecast_periods=2)
    assert result["status"] == "ok"
    assert len(result["forecast"]) == 2
    assert result["forecast"][0]["lower_95"] <= result["forecast"][0]["value"] <= result["forecast"][0]["upper_95"]
