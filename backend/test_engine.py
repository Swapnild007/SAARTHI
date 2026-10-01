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


def test_saarthi_profile_is_goal_oriented():
    from backend.engine import assistant_profile
    profile = assistant_profile("saarthi")
    assert profile["role"] == "personal AI assistant"
    assert "underlying goal" in profile["instruction"]
    assert "Do not fabricate facts" in profile["instruction"]


def test_saarthi_fallback_is_useful_for_general_chat():
    result = SaarthiEngine().run(message="I don't know where to start", assistant="saarthi")
    assert result["assistant"]["id"] == "saarthi"
    assert result["reply"]


def test_saarthi_is_personal_assistant():
    from backend.engine import assistant_profile
    profile = assistant_profile("saarthi")
    assert "personal assistant" in profile["instruction"].lower()
    assert "external integration" in profile["instruction"].lower()


def test_all_six_agents_have_explicit_boundaries():
    from backend.engine import ASSISTANT_PROFILES
    assert set(ASSISTANT_PROFILES) == {"saarthi", "coding", "research", "create", "analyze", "plan"}
    for profile in ASSISTANT_PROFILES.values():
        assert profile.get("boundary")
        assert profile.get("instruction")


def test_specialist_profiles_explicitly_isolate_other_conversations():
    from backend.engine import ASSISTANT_PROFILES
    for assistant in ("coding", "research", "create", "analyze", "plan"):
        instruction = ASSISTANT_PROFILES[assistant]["instruction"].lower()
        assert "separate workspace" in instruction
        assert "never use or reveal messages" in instruction


def test_engine_exposes_selected_agent_boundary():
    result = SaarthiEngine().run(message="hello", assistant="coding")
    assert result["assistant"]["boundary"] == "software engineering only"
