from backend.agent_capabilities import AGENT_CAPABILITIES, AGENT_PLAYBOOKS, build_runtime_context
from backend.agent_knowledge import AGENT_KNOWLEDGE

def test_plan_has_level5_execution_planning_capabilities():
    required = {
        "goal_decomposition", "prioritization", "dependencies", "milestones",
        "risk_planning", "contingencies", "critical_path",
        "execution_tracking", "acceptance_criteria", "scenario_planning"
    }
    assert required.issubset(set(AGENT_CAPABILITIES["plan"]["capabilities"]))

def test_plan_workflow_covers_full_execution_lifecycle():
    sequence = AGENT_PLAYBOOKS["plan"]["sequence"]
    for stage in ["define", "decompose", "prioritize", "sequence", "resource", "validate", "execute", "review"]:
        assert stage in sequence
    gates = set(AGENT_PLAYBOOKS["plan"]["quality_gates"])
    assert {"objective", "dependencies", "constraints", "owners", "milestones", "contingencies", "acceptance"}.issubset(gates)

def test_plan_specialist_knowledge_has_level5_contract():
    knowledge = AGENT_KNOWLEDGE["plan"]
    assert knowledge["mission"]
    assert len(knowledge["non_negotiables"]) >= 10
    contract = knowledge["planning_contract"]
    assert {"objective", "success_criteria", "constraints", "tasks", "dependencies", "critical_path", "milestones", "risks", "contingencies", "acceptance"}.issubset(set(contract["layers"]))
    assert "unknown_resources_not_invented" in knowledge["quality_gates"]["resource_gate"]
    assert "high_impact_decisions_not_assumed_authorized" in knowledge["quality_gates"]["decision_gate"]

def test_plan_failure_modes_cover_false_precision_and_hidden_dependencies():
    failures = set(AGENT_KNOWLEDGE["plan"]["failure_modes"])
    assert "hidden_dependencies" in failures
    assert "false_precision_in_dates_or_effort" in failures
    assert "invented_owner_or_resource" in failures
    assert "milestones_without_acceptance" in failures

def test_plan_output_contract_is_execution_ready():
    required = set(AGENT_KNOWLEDGE["plan"]["output_contract"]["required_sections"])
    assert {"objective", "success_criteria", "workstreams_or_tasks", "dependencies_and_critical_path", "milestones", "risks_and_contingencies", "acceptance_criteria", "open_decisions"}.issubset(required)

def test_plan_industry_context_is_present_for_all_initial_industries():
    industry = AGENT_KNOWLEDGE["plan"]["industry_application"]
    assert {"travel", "financial_services", "healthcare", "retail", "logistics", "manufacturing"}.issubset(industry)

def test_plan_runtime_context_exposes_specialist_knowledge():
    context = build_runtime_context("plan", "manufacturing")
    assert context["assistant"] == "Plan"
    assert context["industry"] == "Manufacturing"
    assert "critical_path" in context["agent_knowledge"]["planning_contract"]["layers"]
