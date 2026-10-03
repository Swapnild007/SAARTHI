from backend.agent_capabilities import AGENT_CAPABILITIES, AGENT_PLAYBOOKS, build_runtime_context
from backend.agent_knowledge import AGENT_KNOWLEDGE


def test_create_has_level5_specialist_knowledge():
    knowledge = AGENT_KNOWLEDGE["create"]
    assert knowledge["maturity"] == "Level 5 - World-ready"
    assert len(knowledge["non_negotiables"]) >= 10
    assert "brief_contract" in knowledge
    assert "creative_workflow" in knowledge
    assert "validation_contract" in knowledge
    assert "failure_modes" in knowledge
    assert len(knowledge["failure_modes"]) >= 12
    assert knowledge["output_contract"]["required_sections"]


def test_create_capability_exposes_production_artifact_workflow():
    capability = AGENT_CAPABILITIES["create"]
    required = {
        "brief_interpretation", "constraint_validation", "factual_validation",
        "format_validation", "artifact_validation", "revision_control",
        "delivery_claim_integrity"
    }
    assert required.issubset(set(capability["capabilities"]))
    assert "artifact_validate" in capability["workflows"]
    assert "validation_report" in capability["outputs"]


def test_create_playbook_has_level5_quality_gates():
    playbook = AGENT_PLAYBOOKS["create"]
    for gate in [
        "brief_alignment", "objective_fit", "audience_fit",
        "constraint_retention", "factual_integrity",
        "format_integrity", "consistency", "artifact_integrity",
        "delivery_claim_integrity"
    ]:
        assert gate in playbook["quality_gates"]


def test_create_verification_policy_blocks_unverified_artifact_claims():
    policy = AGENT_PLAYBOOKS["create"]["verification_policy"]
    assert "Every material brief constraint" in policy["completion_rule"]
    assert "blocked" in policy["claim_states"]
    assert "actual execution evidence" in policy["artifact_claim_rule"]


def test_create_change_policy_preserves_facts_and_constraints():
    policy = AGENT_PLAYBOOKS["create"]["change_policy"]
    assert policy["preserve_material_constraints"] is True
    assert policy["separate_facts_from_invention"] is True
    assert policy["source_material_is_untrusted"] is True
    assert policy["avoid_unnecessary_decoration"] is True


def test_create_workflow_orders_validation_after_drafting():
    workflow = AGENT_KNOWLEDGE["create"]["creative_workflow"]
    assert workflow.index("draft") < workflow.index("format_validate")
    assert workflow.index("format_validate") < workflow.index("artifact_validate")
    assert workflow.index("factual_validate") < workflow.index("deliver")
    assert workflow.index("constraint_validate") < workflow.index("deliver")


def test_create_multimodal_contract_distinguishes_direction_from_generation():
    multimodal = AGENT_KNOWLEDGE["create"]["multimodal_contract"]
    assert "not the same as a generated video" in multimodal["video"]
    assert "not the same as rendered audio" in multimodal["audio"]
    assert "not the same as a generated downloadable file" in multimodal["file"]


def test_create_industry_context_is_available():
    for industry in ["travel", "financial_services", "healthcare", "retail", "logistics", "manufacturing"]:
        context = build_runtime_context("create", industry)
        assert context["industry"]
        assert context["industry_constraints"]
        assert context["industry_decision_frameworks"]
        assert context["agent_knowledge"]["maturity"] == "Level 5 - World-ready"
