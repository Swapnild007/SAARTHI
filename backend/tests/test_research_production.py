from backend.agent_capabilities import AGENT_CAPABILITIES, AGENT_PLAYBOOKS, build_runtime_context
from backend.agent_knowledge import AGENT_KNOWLEDGE

def test_research_has_level5_capabilities():
    required = {"question_framing","source_evaluation","source_quality","recency","cross_checking","citation_integrity","contradiction_handling","uncertainty","provenance"}
    assert required.issubset(set(AGENT_CAPABILITIES["research"]["capabilities"]))

def test_research_playbook_has_evidence_gates():
    sequence = AGENT_PLAYBOOKS["research"]["sequence"]
    assert all(x in sequence for x in ["frame","retrieve","evaluate_sources","compare","synthesize","cite"])
    gates = set(AGENT_PLAYBOOKS["research"]["quality_gates"])
    assert {"source_quality","recency","cross_checking","uncertainty","citation_integrity","contradiction_handling"}.issubset(gates)

def test_research_specialist_contract_rejects_fabricated_evidence():
    k = AGENT_KNOWLEDGE["research"]
    assert len(k["non_negotiables"]) >= 10
    assert "Never invent citations, URLs, quotes, statistics, studies, dates or source contents." in k["non_negotiables"]
    assert "invented_citation" in k["failure_modes"]
    assert "snippet_as_evidence" in k["failure_modes"]
    assert "contradictory_sources_hidden" in k["failure_modes"]

def test_research_output_is_traceable():
    required = set(AGENT_KNOWLEDGE["research"]["output_contract"]["required_sections"])
    assert {"research_question","scope_and_method","key_findings","evidence_and_sources","uncertainty","conclusion"}.issubset(required)

def test_research_has_all_initial_industry_contexts():
    assert {"travel","financial_services","healthcare","retail","logistics","manufacturing"}.issubset(AGENT_KNOWLEDGE["research"]["industry_application"])

def test_research_runtime_context_exposes_specialist_contract():
    context = build_runtime_context("research", "travel")
    assert context["assistant"] == "Research"
    assert "destination" in context["industry_vocabulary"]
    assert "source_inventory" in context["agent_knowledge"]["research_contract"]["layers"]
