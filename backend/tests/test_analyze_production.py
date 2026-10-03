from backend.agent_capabilities import AGENT_CAPABILITIES, AGENT_PLAYBOOKS, INDUSTRY_PACKS, build_runtime_context
from backend.agent_knowledge import AGENT_KNOWLEDGE


def test_analyze_has_level5_reasoning_contract():
    knowledge = AGENT_KNOWLEDGE["analyze"]
    assert knowledge["mission"]
    assert len(knowledge["non_negotiables"]) >= 8
    assert knowledge["analysis_contract"]["layers"]
    assert "confirmed" in knowledge["analysis_contract"]["evidence_status"]
    assert "unknown" in knowledge["analysis_contract"]["evidence_status"]
    assert len(knowledge["workflow"]) >= 10
    assert knowledge["methods"]["root_cause"]
    assert knowledge["methods"]["risk"]
    assert knowledge["methods"]["tradeoff"]
    assert len(knowledge["failure_modes"]) >= 10
    assert knowledge["output_contract"]["required_sections"]


def test_analyze_capability_exposes_production_reasoning():
    capability = AGENT_CAPABILITIES["analyze"]
    required = {
        "source_inventory", "hypothesis_generation", "alternative_hypotheses",
        "contradiction_detection", "root_cause", "incident_analysis",
        "causal_reasoning", "confidence_assessment", "traceability",
        "next_check_design"
    }
    assert required.issubset(set(capability["capabilities"]))
    assert "compare_alternatives" in capability["workflows"]
    assert "verify_traceability" in capability["workflows"]
    assert "confidence_statement" in capability["outputs"]


def test_analyze_playbook_has_explicit_reasoning_gates():
    playbook = AGENT_PLAYBOOKS["analyze"]
    for gate in [
        "observation_interpretation_separation",
        "alternatives",
        "contradictions",
        "causal_reasoning",
        "confidence",
        "traceability",
        "action_safety",
    ]:
        assert gate in playbook["quality_gates"]


def test_analyze_industry_context_is_specialized():
    for industry in INDUSTRY_PACKS:
        context = build_runtime_context("analyze", industry)
        assert context["agent_knowledge"]["industry_application"]
        assert context["industry"]
        assert context["industry_mapping"] if "industry_mapping" in context else True
        assert context["industry_constraints"]
        assert context["industry_decision_frameworks"]


def test_analyze_decision_rule_rejects_speculation():
    rule = AGENT_KNOWLEDGE["analyze"]["decision_rule"]
    assert "insufficient" in rule
    assert "speculation" in rule
