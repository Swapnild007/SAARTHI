from backend.verification import verify_run
from backend.work_product import build_work_product


def test_model_response_is_not_mislabeled_as_fact_checked():
    result = verify_run(
        objective="Explain why sales fell",
        reply="Sales may have fallen due to lower demand.",
        tool_results={},
        execution="completed",
        provider="openrouter",
    )
    assert result["status"] == "runtime_checked"
    assert "not been independently fact-checked" in result["scope"]
    assert result["limitations"]


def test_empty_objective_or_reply_fails_verification():
    result = verify_run(
        objective="",
        reply="",
        execution="completed",
        provider="test",
    )
    assert result["status"] == "failed"
    assert {check["name"] for check in result["checks"] if check["status"] == "failed"} == {
        "objective_present",
        "response_present",
    }


def test_incomplete_execution_is_not_reported_as_verified():
    result = verify_run(
        objective="Run a task",
        reply="Partial result",
        execution="timed-out-safely",
        provider="openrouter",
    )
    assert result["status"] == "incomplete"
    assert result["checks"][2]["status"] == "blocked"


def test_deterministic_tool_result_is_scoped_to_that_result():
    result = verify_run(
        objective="Calculate 2 + 2",
        reply="The answer is 4.",
        tool_results={"system.calculate": {"expression": "2 + 2", "value": 4}},
        execution="completed",
        provider="system.calculate",
    )
    assert result["status"] == "partially_verified"
    assert "not every sentence" in result["limitations"][0]


def test_work_product_verification_does_not_overclaim():
    result = build_work_product(
        objective="Summarize the options",
        intent="chat",
        reply="Option A is cheaper.",
        verification={"claims": "response generated from available execution context"},
    )
    assert result["version"] == "1.0"
    assert result["verification"]["status"] == "runtime_checked"
    assert "not been independently fact-checked" in result["verification"]["scope"]
