from backend.agent_capabilities import AGENT_CAPABILITIES, AGENT_PLAYBOOKS, INDUSTRY_PACKS, build_runtime_context
from backend.agent_knowledge import AGENT_KNOWLEDGE


def test_all_seven_agents_have_production_contract_basics():
    expected = {"saarthi", "coding", "research", "create", "data_analyst", "analyze", "plan"}
    assert set(AGENT_CAPABILITIES) == expected
    assert set(AGENT_PLAYBOOKS) == expected
    assert set(AGENT_KNOWLEDGE) == expected
    for agent in expected:
        assert AGENT_CAPABILITIES[agent]["capabilities"]
        assert AGENT_CAPABILITIES[agent]["workflows"]
        assert AGENT_CAPABILITIES[agent]["outputs"]
        assert AGENT_PLAYBOOKS[agent]["sequence"]
        assert AGENT_PLAYBOOKS[agent]["quality_gates"]


def test_saarthi_orchestration_contract_is_explicit():
    knowledge = AGENT_KNOWLEDGE["saarthi"]
    contract = knowledge["orchestration_contract"]
    assert contract["ownership"]
    assert contract["routing_basis"]
    assert contract["context_envelope"]
    assert contract["verification"]
    assert contract["recovery"]
    assert contract["anti_patterns"]
    assert set(contract["specialist_selection"]) == {
        "coding", "research", "create", "data_analyst", "analyze", "plan"
    }


def test_runtime_context_exposes_orchestration_contract_without_backend_changes():
    context = build_runtime_context("saarthi", "retail")
    assert context["industry"] == "Retail & E-commerce"
    assert context["agent_knowledge"]["orchestration_contract"]["ownership"]
    assert "inventory" in context["industry_vocabulary"]
    assert context["agent_playbook"]["role"] == "orchestrator"


def test_all_initial_industries_have_agent_mappings_and_kpis():
    assert len(INDUSTRY_PACKS) == 6
    for pack in INDUSTRY_PACKS.values():
        assert pack["vocabulary"]
        assert pack["workflows"]
        assert pack["kpis"]
        assert pack["constraints"]
        assert pack["decision_frameworks"]
        assert pack["artifacts"]
