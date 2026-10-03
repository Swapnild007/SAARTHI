from backend.agent_capabilities import AGENT_CAPABILITIES, AGENT_PLAYBOOKS, build_runtime_context
from backend.agent_knowledge import AGENT_KNOWLEDGE


def test_coding_has_level5_engineering_contract():
    knowledge = AGENT_KNOWLEDGE["coding"]
    required = {
        "repository_inspection", "define_acceptance_criteria",
        "map_dependencies_and_risk", "implement", "run_targeted_tests",
        "run_regression_suite", "security_review", "review_diff",
        "verify_artifacts_and_deployment_claims"
    }
    assert required.issubset(set(knowledge["workflow"]))
    assert len(knowledge["non_negotiables"]) >= 9
    assert knowledge["engineering_contract"]["verification_levels"]
    assert knowledge["testing_strategy"]["negative"]
    assert knowledge["security_contract"]
    assert len(knowledge["failure_modes"]) >= 10
    assert knowledge["output_contract"]["required_sections"]


def test_coding_capability_exposes_production_engineering():
    capability = AGENT_CAPABILITIES["coding"]
    required = {
        "repository_inspection", "requirements_modeling", "negative_testing",
        "regression_testing", "security_review", "dependency_review",
        "diff_review", "deployment_readiness"
    }
    assert required.issubset(set(capability["capabilities"]))
    assert "verify_artifacts" in capability["workflows"]
    assert "implementation_report" in capability["outputs"]


def test_coding_playbook_has_strict_quality_gates():
    playbook = AGENT_PLAYBOOKS["coding"]
    for gate in [
        "requirements", "correctness", "regression_safety",
        "negative_paths", "security", "dependency_integrity",
        "deployment_readiness", "claim_integrity"
    ]:
        assert gate in playbook["quality_gates"]


def test_coding_industry_context_is_available():
    for industry in ["travel", "financial_services", "healthcare", "retail", "logistics", "manufacturing"]:
        context = build_runtime_context("coding", industry)
        assert context["industry"]
        assert context["industry_constraints"]
        assert context["industry_decision_frameworks"]


def test_coding_completion_rule_prevents_unverified_claims():
    rule = AGENT_KNOWLEDGE["coding"]["output_contract"]["claim_rule"]
    assert "Only claim" in rule
    assert "actually executed" in rule


def test_coding_playbook_has_level5_verification_policy():
    playbook = AGENT_PLAYBOOKS["coding"]
    policy = playbook["verification_policy"]
    assert policy["levels"] == ["static", "targeted_test", "regression_suite", "integration", "deployment"]
    assert "Every material acceptance criterion" in policy["completion_rule"]
    assert "blocked" in policy["claim_states"]
    assert "unverified" in policy["completion_rule"]


def test_coding_change_policy_preserves_repository_integrity():
    policy = AGENT_PLAYBOOKS["coding"]["change_policy"]
    assert policy["preferred_change"] == "smallest_coherent_change"
    assert policy["preserve_compatible_behavior"] is True
    assert policy["generated_artifacts"] == "prefer_source_or_regeneration"
    assert policy["secrets"] == "never_commit_or_expose"
    assert "confirmation" in policy["high_impact_actions"]
    assert "rollback" in policy["high_impact_actions"]


def test_coding_workflow_has_explicit_verification_boundaries():
    workflow = AGENT_KNOWLEDGE["coding"]["workflow"]
    assert workflow.index("run_targeted_tests") < workflow.index("run_regression_suite")
    assert workflow.index("run_regression_suite") < workflow.index("security_review")
    assert workflow.index("security_review") < workflow.index("review_diff")
    assert workflow.index("review_diff") < workflow.index("verify_artifacts_and_deployment_claims")
