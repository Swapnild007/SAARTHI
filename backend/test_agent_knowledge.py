from backend.agent_knowledge import AGENT_KNOWLEDGE, KNOWLEDGE_SOURCES, knowledge_for
from backend.agent_capabilities import build_runtime_context


def test_all_seven_agents_have_knowledge():
    expected = {"saarthi", "coding", "research", "create", "data_analyst", "analyze", "plan"}
    assert expected == set(AGENT_KNOWLEDGE)
    for agent in expected:
        pack = knowledge_for(agent)
        assert pack["principles"]
        assert pack["workflow"]
        assert pack["quality_gates"]


def test_data_analyst_knowledge_is_runtime_visible():
    runtime = build_runtime_context("data_analyst")
    assert "agent_knowledge" in runtime
    assert "provenance" in runtime["agent_knowledge"]["quality_gates"]
    assert "deterministic calculations outside the language model whenever possible." in runtime["agent_knowledge"]["principles"]


def test_knowledge_sources_are_public_and_explicit():
    assert len(KNOWLEDGE_SOURCES) >= 5
    assert all(item["url"].startswith("https://") for item in KNOWLEDGE_SOURCES)
