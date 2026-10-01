from backend.engine import ASSISTANT_PROFILES, SaarthiEngine, classify, build_plan


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
    assert "Do not fabricate facts" in profile["instruction"]


def test_saarthi_fallback_is_useful_for_general_chat():
    result = SaarthiEngine().run(message="I don't know where to start", assistant="saarthi")
    assert result["assistant"]["id"] == "saarthi"
    assert result["reply"]


def test_saarthi_is_personal_assistant():
    from backend.engine import assistant_profile
    profile = assistant_profile("saarthi")
    assert "personal assistant" in profile["instruction"].lower()


def test_all_six_agents_have_explicit_boundaries():
    from backend.engine import ASSISTANT_PROFILES
    assert set(ASSISTANT_PROFILES) == {"saarthi", "coding", "research", "create", "data_analyst", "analyze", "plan"}
    for profile in ASSISTANT_PROFILES.values():
        assert profile.get("boundary")
        assert profile.get("instruction")


def test_specialist_profiles_explicitly_isolate_other_conversations():
    from backend.engine import ASSISTANT_PROFILES
    for assistant in ("coding", "research", "create", "data_analyst", "analyze", "plan"):
        instruction = ASSISTANT_PROFILES[assistant]["instruction"].lower()
        assert "separate workspace" in instruction
        assert "never use or reveal messages" in instruction


def test_engine_exposes_selected_agent_boundary():
    result = SaarthiEngine().run(message="hello", assistant="coding")
    assert result["assistant"]["boundary"] == "software engineering only"


def test_coding_rejects_non_coding_request():
    result = SaarthiEngine().run(message="what is the weather today?", assistant="coding")
    assert result["execution"] == "blocked-by-scope"
    assert result["provider"] == "boundary-guard"
    assert "software engineering only" in result["reply"]


def test_research_rejects_implementation_request():
    result = SaarthiEngine().run(message="implement this Python function", assistant="research")
    assert result["execution"] == "blocked-by-scope"


def test_create_rejects_debugging_request():
    result = SaarthiEngine().run(message="debug this Python script", assistant="create")
    assert result["execution"] == "blocked-by-scope"


def test_analyze_rejects_writing_request():
    result = SaarthiEngine().run(message="write an email to my manager", assistant="analyze")
    assert result["execution"] == "blocked-by-scope"


def test_plan_rejects_coding_request():
    result = SaarthiEngine().run(message="debug this code", assistant="plan")
    assert result["execution"] == "blocked-by-scope"


def test_coding_accepts_software_request():
    result = SaarthiEngine().run(message="write a Python function to parse JSON", assistant="coding")
    assert result["execution"] == "completed"
    assert result["assistant"]["id"] == "coding"


def test_all_seven_agents_use_deterministic_time_before_model():
    for assistant in ASSISTANT_PROFILES:
        engine = SaarthiEngine()
        engine.cloud.generate = lambda **kwargs: (_ for _ in ()).throw(AssertionError("LLM must not run for time"))
        result = engine.run(message="What is current time", assistant=assistant, context={"timezone": "Asia/Kolkata"})
        assert result["ok"] is True
        assert result["intent"]["name"] == "time"
        assert result["provider"] == "system.time"
        assert result["execution"] == "completed"
        assert result["verification"]["verified"] is True
        assert result["tool_results"]["system.time"]["timezone"] == "Asia/Kolkata"
        assert "general conversation" not in result["reply"]


def test_all_seven_agents_use_deterministic_date_before_model():
    for assistant in ASSISTANT_PROFILES:
        engine = SaarthiEngine()
        engine.cloud.generate = lambda **kwargs: (_ for _ in ()).throw(AssertionError("LLM must not run for date"))
        result = engine.run(message="What is today's date", assistant=assistant, context={"timezone": "Asia/Kolkata"})
        assert result["intent"]["name"] == "date"
        assert result["provider"] == "system.date"
        assert result["tool_results"]["system.date"]["timezone"] == "Asia/Kolkata"
        assert "general conversation" not in result["reply"]


def test_calculation_is_deterministic_and_model_free():
    engine = SaarthiEngine()
    engine.cloud.generate = lambda **kwargs: (_ for _ in ()).throw(AssertionError("LLM must not run for calculation"))
    result = engine.run(message="What is 25 * 48")
    assert result["intent"]["name"] == "calculate"
    assert result["provider"] == "system.calculate"
    assert result["tool_results"]["system.calculate"]["value"] == 1200.0


def test_unit_conversion_is_deterministic_and_model_free():
    engine = SaarthiEngine()
    engine.cloud.generate = lambda **kwargs: (_ for _ in ()).throw(AssertionError("LLM must not run for conversion"))
    result = engine.run(message="Convert 10 km to miles")
    assert result["intent"]["name"] == "convert"
    assert result["provider"] == "system.convert"
    assert abs(result["tool_results"]["system.convert"]["result"] - 6.213711922) < 1e-9


def test_deterministic_tools_are_registered_in_shared_registry():
    names = SaarthiEngine().tools.names()
    assert {"system.time", "system.date", "system.calculate", "system.convert", "system.status"} <= set(names)


def test_all_seven_agents_have_structured_capabilities():
    from backend.agent_capabilities import AGENT_CAPABILITIES
    assert set(AGENT_CAPABILITIES) == {"saarthi", "coding", "research", "create", "data_analyst", "analyze", "plan"}
    for capability in AGENT_CAPABILITIES.values():
        assert capability["capabilities"]
        assert capability["workflows"]
        assert capability["outputs"]


def test_travel_industry_pack_maps_to_multiple_agents():
    from backend.agent_capabilities import industry_pack, build_runtime_context
    pack = industry_pack("travel")
    assert pack["name"] == "Travel & Tourism"
    assert "itinerary" in pack["workflows"]
    assert "destination_research" in pack["agent_mapping"]["research"]
    runtime = build_runtime_context("plan", "travel")
    assert runtime["industry"] == "Travel & Tourism"
    assert "itinerary" in runtime["industry_agent_mapping"]


def test_runtime_returns_agent_capabilities():
    result = SaarthiEngine().run(message="build a project roadmap", assistant="plan", context={"industry": "travel"})
    assert result["assistant"]["id"] == "plan"
    assert result["assistant"]["capabilities"]["name"] == "Plan"
    assert result["assistant"]["industry"] == "Travel & Tourism"


def test_data_analysis_engine_profiles_and_aggregates():
    from backend.data_analysis import analyze_dataset, group_by, percentage_change, correlation
    columns = ["LOB", "Handled", "AHT"]
    rows = [
        {"LOB": "CountyCare", "Handled": "100", "AHT": "600"},
        {"LOB": "CountyCare", "Handled": "120", "AHT": "660"},
        {"LOB": "Premera", "Handled": "80", "AHT": "540"},
    ]
    result = analyze_dataset(columns, rows)
    assert result["profile"]["row_count"] == 3
    assert "Handled" in result["numeric_columns"]
    grouped = group_by(rows, "LOB", "Handled", "sum")
    assert {x["LOB"]: x["Handled"] for x in grouped}["CountyCare"] == 220.0
    assert percentage_change(100, 120) == 20.0
    assert correlation(rows, "Handled", "AHT") is not None


def test_data_analyst_runtime_returns_computed_profile():
    import base64
    from backend.engine import SaarthiEngine
    csv_text = "LOB,Handled,AHT\nCountyCare,100,600\nCountyCare,120,660\nPremera,80,540\n"
    data = base64.b64encode(csv_text.encode()).decode()
    result = SaarthiEngine().run(
        message="analyze this dataset",
        assistant="data_analyst",
        context={"attachments": [{"name": "sample.csv", "type": "text/csv", "data": data}]},
    )
    assert result["execution"] == "completed"
    analysis = result["tool_results"]["data.analysis"]
    assert analysis["profile"]["row_count"] == 3
    assert analysis["profile"]["duplicate_rows"] == 0


def test_data_analyst_chart_is_built_from_attachment_data():
    import base64
    from backend.engine import SaarthiEngine
    csv_text = "LOB,Handled\nCountyCare,100\nPremera,80\nMPC,90\n"
    data = base64.b64encode(csv_text.encode()).decode()
    result = SaarthiEngine().run(
        message="create a bar chart",
        assistant="data_analyst",
        context={"attachments": [{"name": "sample.csv", "type": "text/csv", "data": data}]},
    )
    chart = result["tool_results"]["data.chart"]
    assert chart["chartType"] == "bar"
    assert chart["data"][0]["Handled"] == "100"
