from backend.engine import SaarthiEngine, classify, build_plan


def test_explicit_research_command():
    intent = classify("/research compare two approaches")
    assert intent.name == "research"
    assert intent.confidence == 1.0


def test_ui_task_alias():
    intent = classify("finish this", "tasks")
    assert intent.name == "task"


def test_plan_contains_understand_and_response():
    plan = build_plan(classify("plan my day"))
    ids = [step.id for step in plan]
    assert ids[0] == "understand"
    assert ids[-1] == "respond"


def test_engine_returns_run_contract():
    result = SaarthiEngine().run(message="what can you do", mode="help")
    assert result["ok"] is True
    assert result["run_id"].startswith("run_")
    assert result["intent"]["name"] == "help"
    assert result["execution"] == "completed"
    assert result["verification"]["verified"] is True


def test_assistant_profile_is_returned():
    result = SaarthiEngine().run(message="review this function", assistant="coding")
    assert result["assistant"]["id"] == "coding"
    assert result["assistant"]["name"] == "AI Coding"


def test_unknown_assistant_falls_back_to_saarthi():
    result = SaarthiEngine().run(message="hello", assistant="unknown")
    assert result["assistant"]["id"] == "saarthi"
