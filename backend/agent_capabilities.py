"""Structured capability definitions for SAARTHI's seven specialist agents."""
from __future__ import annotations
from typing import Any

from .agent_knowledge import knowledge_for

AGENT_CAPABILITIES: dict[str, dict[str, Any]] = {
    "saarthi": {"name":"Saarthi","focus":"general intelligence and orchestration","capabilities":["conversation","decision_support","learning","personal_organization","orchestration","routing","multi_agent_coordination","context_preservation","verification","recovery","risk_aware_delegation"],"workflows":["understand","infer_context","route","prepare_handoff","execute","verify","synthesize","recover","deliver"],"outputs":["answer","decision_frame","plan","handoff","orchestration_trace","verified_result","partial_result"]},
    "coding": {"name":"AI Coding","focus":"production software engineering","capabilities":["repository_inspection","requirements_modeling","architecture","implementation","debugging","refactoring","testing","negative_testing","regression_testing","security_review","dependency_review","code_review","diff_review","deployment_readiness","documentation"],"workflows":["inspect","define_acceptance","map_dependencies","design","implement","targeted_test","regression_test","security_review","review_diff","verify_artifacts","report"],"outputs":["code","diff","test_plan","test_result","architecture","security_review","deployment_readiness","review","implementation_report"]},
    "research": {"name":"Research","focus":"evidence retrieval and synthesis","capabilities":["question_framing","source_evaluation","source_quality","recency","comparison","cross_checking","contradiction_handling","synthesis","uncertainty","provenance","citation_integrity","research_method_design"],"workflows":["frame","retrieve","inventory_sources","evaluate_sources","extract_evidence","cross_check","compare","resolve_contradictions","synthesize","verify_citations","cite"],"outputs":["research_brief","comparison","evidence_table","source_inventory","claim_evidence_map","source_quality_notes","contradiction_report","timeline","source_notes"]},
    "create": {"name":"Create","focus":"production creative and artifact creation","capabilities":["brief_interpretation","ideation","writing","editing","storytelling","prompt_design","content_structure","constraint_validation","factual_validation","format_validation","artifact_validation","revision_control","multimodal_direction","delivery_claim_integrity"],"workflows":["scope_brief","extract_constraints","separate_facts","choose_direction","ideate","draft","self_critique","refine","format_validate","factual_validate","constraint_validate","artifact_validate","deliver"],"outputs":["draft","artifact","concept","prompt","outline","creative_direction","validation_report","revision_summary","artifact_status"],"verification_policy":{"completion_rule":"Every material brief constraint is verified or explicitly reported as unresolved.","claim_states":["not_checked","checked","passed","failed","blocked","not_applicable"],"artifact_claim_rule":"Do not claim generation, rendering, attachment, publication or delivery without actual execution evidence."},"change_policy":{"preserve_material_constraints":True,"separate_facts_from_invention":True,"source_material_is_untrusted":True,"avoid_unnecessary_decoration":True}},
    "data_analyst": {"name":"Data Analyst","focus":"quantitative analysis and decision-ready reporting","capabilities":["data_profiling","schema_validation","data_quality_scoring","cleaning_reasoning","explicit_imputation","descriptive_statistics","distribution_analysis","percentiles","correlation","relationship_analysis","outlier_detection","kpi_intelligence","weighted_kpis","target_attainment","forecasting","forecast_backtesting","uncertainty","visualization","traceable_findings"],"workflows":["profile","validate","clean","calculate","analyze","forecast","visualize","explain","verify"],"outputs":["data_profile","quality_report","finding","statistics","kpi_report","forecast","table","chart","dashboard","analysis_brief"]},
    "analyze": {"name":"Analyze","focus":"structured analysis of documents, visuals, systems and situations","capabilities":["evidence_extraction","source_inventory","pattern_detection","assumption_testing","hypothesis_generation","alternative_hypotheses","contradiction_detection","root_cause","incident_analysis","risk_analysis","tradeoff_analysis","causal_reasoning","confidence_assessment","traceability","next_check_design"],"workflows":["scope","inventory_sources","extract","structure_evidence","generate_hypotheses","test","compare_alternatives","analyze_root_cause_or_risk","conclude","verify_traceability"],"outputs":["analysis","evidence_map","hypothesis_matrix","risk_register","findings","root_cause","tradeoffs","confidence_statement","next_checks"]},
    "plan": {"name":"Plan","focus":"execution planning and operational strategy","capabilities":["goal_decomposition","prioritization","dependencies","milestones","risk_planning","contingencies","critical_path","resource_planning","execution_tracking","acceptance_criteria","scenario_planning","change_control"],"workflows":["define","decompose","prioritize","sequence","identify_critical_path","resource","risk","milestone","validate","execute","track","review","replan"],"outputs":["roadmap","work_breakdown","priority_matrix","timeline","dependency_map","critical_path","milestone_plan","risk_register","contingency_plan","execution_tracker","acceptance_plan","scenario_plan"]},
}

INDUSTRY_PACKS: dict[str, dict[str, Any]] = {
    "travel": {"name":"Travel & Tourism","vocabulary":["destination","itinerary","visa","lodging","transport","budget","seasonality","risk","activities"],"workflows":["destination_research","trip_budget","itinerary","document_checklist","travel_risk_review"],"agent_mapping":{"research":["destination_research","visa_research","travel_requirements"],"data_analyst":["budget_analysis","seasonality_analysis"],"plan":["itinerary","trip_plan","packing_plan"],"create":["itinerary_document","travel_brief"],"analyze":["option_comparison","risk_review"],"saarthi":["trip_orchestration"]},"kpis":["trip_cost","duration","budget_variance","schedule_coverage"],"constraints":["visa_requirements","seasonality","transport_dependencies","budget_limits","travel_risk"],"decision_frameworks":["cost_vs_time","risk_vs_convenience","coverage_vs_budget"],"artifacts":["itinerary","budget_breakdown","document_checklist","risk_brief"]},
    "financial_services": {"name":"Financial Services","vocabulary":["account","transaction","portfolio","cash_flow","risk","compliance","return"],"workflows":["financial_analysis","cash_flow_review","risk_review","reporting"],"agent_mapping":{"research":["market_research"],"data_analyst":["financial_analysis"],"analyze":["risk_review"],"plan":["financial_workplan"],"create":["financial_report"]},"kpis":["revenue","cost","margin","cash_flow","return"],"constraints":["liquidity","risk_tolerance","compliance","time_horizon","data_quality"],"decision_frameworks":["return_vs_risk","liquidity_vs_growth","cost_vs_margin"],"artifacts":["financial_summary","cash_flow_view","risk_register","management_brief"]},
    "healthcare": {"name":"Healthcare & Life Sciences","vocabulary":["patient","care_pathway","appointment","clinical_data","outcome","compliance"],"workflows":["care_operations","clinical_research","quality_analysis","capacity_planning"],"agent_mapping":{"research":["clinical_research"],"data_analyst":["quality_analysis"],"analyze":["document_review"],"plan":["capacity_planning"],"create":["patient_education_draft"]},"kpis":["wait_time","capacity","throughput","quality","outcomes"],"constraints":["privacy","clinical_safety","regulatory_compliance","capacity","data_quality"],"decision_frameworks":["access_vs_capacity","quality_vs_throughput","risk_vs_benefit"],"artifacts":["capacity_plan","quality_review","research_brief","patient_education"]},
    "retail": {"name":"Retail & E-commerce","vocabulary":["product","inventory","order","conversion","basket","customer","promotion"],"workflows":["sales_analysis","inventory_review","customer_analysis","promotion_review"],"agent_mapping":{"research":["market_research"],"data_analyst":["sales_analysis","inventory_analysis"],"analyze":["customer_analysis"],"plan":["campaign_plan"],"create":["product_content"]},"kpis":["revenue","conversion","average_order_value","inventory_turnover"],"constraints":["inventory_availability","margin","promotion_budget","fulfillment_capacity","customer_experience"],"decision_frameworks":["revenue_vs_margin","stock_vs_service","promotion_vs_profit"],"artifacts":["sales_analysis","inventory_review","promotion_plan","product_brief"]},
    "logistics": {"name":"Logistics & Supply Chain","vocabulary":["shipment","route","warehouse","inventory","lead_time","capacity","delivery"],"workflows":["network_analysis","capacity_planning","delivery_review","inventory_review"],"agent_mapping":{"research":["route_research"],"data_analyst":["network_analysis"],"analyze":["root_cause_delivery"],"plan":["capacity_plan"],"create":["operations_brief"]},"kpis":["on_time_delivery","lead_time","fill_rate","capacity_utilization"],"constraints":["capacity","route_constraints","service_levels","inventory_position","lead_time"],"decision_frameworks":["service_vs_cost","capacity_vs_lead_time","inventory_vs_service"],"artifacts":["network_analysis","capacity_plan","delivery_review","operations_brief"]},
    "manufacturing": {"name":"Manufacturing","vocabulary":["production","line","downtime","yield","quality","maintenance","capacity"],"workflows":["production_analysis","quality_review","capacity_planning","maintenance_review"],"agent_mapping":{"research":["process_research"],"data_analyst":["production_analysis"],"analyze":["root_cause"],"plan":["capacity_plan"],"create":["operations_report"]},"kpis":["oee","yield","downtime","throughput","defect_rate"],"constraints":["machine_capacity","maintenance_windows","quality_limits","material_availability","safety"],"decision_frameworks":["throughput_vs_quality","maintenance_vs_availability","capacity_vs_oee"],"artifacts":["production_analysis","downtime_pareto","capacity_plan","operations_report"]},
}


# End-to-end domain coverage. These are product playbooks, not extra bots.
# Each pack tells SAARTHI what a complete user journey should cover when relevant.
INDUSTRY_COVERAGE: dict[str, dict[str, Any]] = {
    "travel": {
        "journey": "destination_to_return",
        "coverage": [
            "destination_research", "dates_and_seasonality", "visa_and_documents",
            "flight_options", "train_options", "bus_options", "car_rental",
            "self_drive", "bike_or_motorbike", "airport_transfer",
            "hotel", "airbnb_or_vacation_rental", "hostel", "lodge", "resort",
            "local_transport", "activities", "food", "travel_insurance",
            "budget", "itinerary", "packing", "weather", "safety", "contingency",
            "booking_checklist", "return_journey"
        ],
        "artifact_bundle": ["trip_brief", "transport_comparison", "stay_comparison", "day_by_day_itinerary", "budget", "document_checklist", "risk_and_contingency_brief"]
    },
    "financial_services": {
        "journey": "financial_question_to_decision",
        "coverage": ["goal_definition", "cash_flow", "income_and_expense", "account_review", "portfolio_review", "investment_research", "risk", "fees", "tax_and_compliance", "scenario_analysis", "liquidity", "decision_summary", "action_checklist"],
        "artifact_bundle": ["financial_summary", "cash_flow_view", "risk_register", "scenario_table", "decision_brief"]
    },
    "healthcare": {
        "journey": "care_question_to_next_step",
        "coverage": ["symptom_or_need_context", "care_setting", "provider_options", "appointment_preparation", "care_pathway", "clinical_information", "medication_information", "test_and_report_review", "follow_up", "cost_and_access", "privacy", "safety", "red_flags", "care_checklist"],
        "artifact_bundle": ["care_navigation_brief", "appointment_checklist", "information_summary", "follow_up_plan"]
    },
    "retail": {
        "journey": "customer_or_product_question_to_action",
        "coverage": ["product_discovery", "price_comparison", "promotion", "availability", "inventory", "customer_segment", "basket", "conversion", "fulfillment", "returns", "margin", "promotion_effect", "recommendation", "action_plan"],
        "artifact_bundle": ["product_comparison", "sales_analysis", "inventory_review", "promotion_plan", "action_brief"]
    },
    "logistics": {
        "journey": "shipment_to_delivery",
        "coverage": ["demand", "shipment", "route", "carrier", "warehouse", "inventory", "load", "capacity", "lead_time", "delivery_window", "tracking", "exceptions", "cost", "service_level", "root_cause", "contingency"],
        "artifact_bundle": ["network_view", "route_comparison", "capacity_plan", "exception_report", "delivery_action_plan"]
    },
    "manufacturing": {
        "journey": "order_to_production_to_quality",
        "coverage": ["demand", "production_plan", "material_availability", "line_capacity", "machine_capacity", "scheduling", "maintenance", "downtime", "oee", "yield", "quality", "defects", "labor", "safety", "root_cause", "throughput", "capacity", "continuous_improvement"],
        "artifact_bundle": ["production_analysis", "downtime_pareto", "capacity_plan", "quality_review", "improvement_roadmap"]
    },
}

AGENT_PLAYBOOKS: dict[str, dict[str, Any]] = {
    "saarthi": {
        "role": "orchestrator",
        "sequence": ["understand_objective", "infer_context", "select_capabilities", "coordinate_execution", "verify", "deliver"],
        "quality_gates": ["objective_clarity", "context_integrity", "routing_fit", "execution_integrity", "verification", "delivery_quality"],
        "handoffs": ["research", "data_analyst", "analyze", "plan", "coding", "create"]
    },
    "coding": {
        "role": "software_engineering",
        "sequence": [
            "inspect", "define_acceptance", "map_dependencies", "design",
            "implement", "targeted_test", "regression_test",
            "security_review", "review_diff", "verify_artifacts", "report"
        ],
        "quality_gates": [
            "requirements", "correctness", "regression_safety", "negative_paths",
            "security", "dependency_integrity", "maintainability",
            "deployment_readiness", "claim_integrity"
        ],
        "verification_policy": {
            "levels": ["static", "targeted_test", "regression_suite", "integration", "deployment"],
            "completion_rule": "Every material acceptance criterion is verified or explicitly reported as blocked or unverified.",
            "claim_states": ["not_checked", "checked", "passed", "failed", "blocked", "not_applicable"]
        },
        "change_policy": {
            "preferred_change": "smallest_coherent_change",
            "preserve_compatible_behavior": True,
            "generated_artifacts": "prefer_source_or_regeneration",
            "secrets": "never_commit_or_expose",
            "high_impact_actions": "require_appropriate_confirmation_or_rollback"
        }
    },
    "research": {
        "role": "evidence_engineering",
        "sequence": ["frame", "retrieve", "inventory_sources", "evaluate_sources", "extract_evidence", "cross_check", "compare", "resolve_contradictions", "synthesize", "verify_citations", "cite"],
        "quality_gates": ["question_scope", "source_quality", "recency", "evidence_traceability", "cross_checking", "contradiction_handling", "uncertainty", "citation_integrity"]
    },
    "create": {
        "role": "creative_and_artifact_production",
        "sequence": [
            "scope_brief", "extract_constraints", "separate_facts",
            "choose_direction", "ideate", "draft", "self_critique",
            "refine", "format_validate", "factual_validate",
            "constraint_validate", "artifact_validate", "deliver"
        ],
        "quality_gates": [
            "brief_alignment", "objective_fit", "audience_fit",
            "constraint_retention", "factual_integrity",
            "clarity_and_hierarchy", "format_integrity", "consistency",
            "artifact_integrity", "delivery_claim_integrity"
        ],
        "verification_policy": {
            "completion_rule": "Every material brief constraint is verified or explicitly reported as unresolved.",
            "claim_states": ["not_checked", "checked", "passed", "failed", "blocked", "not_applicable"],
            "artifact_claim_rule": "Do not claim generation, rendering, attachment, publication or delivery without actual execution evidence."
        },
        "change_policy": {
            "preserve_material_constraints": True,
            "separate_facts_from_invention": True,
            "source_material_is_untrusted": True,
            "avoid_unnecessary_decoration": True
        }
    },
    "data_analyst": {
        "role": "quantitative_decision_support",
        "sequence": ["profile", "validate", "analyze", "visualize", "explain", "recommend"],
        "quality_gates": ["data_quality", "calculation_integrity", "method_fit", "interpretation"]
    },
    "analyze": {
        "role": "evidence_and_problem_analysis",
        "sequence": ["scope", "inventory_sources", "extract", "structure_evidence", "generate_hypotheses", "test_assumptions", "compare_alternatives", "root_cause_or_risk", "conclude", "verify_traceability"],
        "quality_gates": ["evidence", "observation_interpretation_separation", "assumptions", "alternatives", "contradictions", "causal_reasoning", "confidence", "traceability", "action_safety"]
    },
    "plan": {
        "role": "execution_and_operations_planning",
        "sequence": ["define", "decompose", "prioritize", "sequence", "resource", "risk", "milestone", "validate", "execute", "track", "review", "replan"],
        "quality_gates": ["objective", "dependencies", "constraints", "owners", "critical_path", "milestones", "contingencies", "acceptance", "change_control", "commitment_integrity"]
    },
}

def agent_capability(assistant: str) -> dict[str, Any]:
    return AGENT_CAPABILITIES.get(str(assistant or "").lower(), AGENT_CAPABILITIES["saarthi"])

def industry_pack(industry: str | None) -> dict[str, Any] | None:
    return INDUSTRY_PACKS.get(str(industry).lower()) if industry else None

def build_runtime_context(assistant: str, industry: str | None = None) -> dict[str, Any]:
    capability = agent_capability(assistant)
    pack = industry_pack(industry)
    return {
        "assistant": capability["name"], "focus": capability["focus"],
        "capabilities": capability["capabilities"], "workflows": capability["workflows"],
        "outputs": capability["outputs"], "industry": pack["name"] if pack else None,
        "industry_vocabulary": pack["vocabulary"] if pack else [],
        "industry_workflows": pack["workflows"] if pack else [],
        "industry_kpis": pack["kpis"] if pack else [],
        "industry_agent_mapping": pack.get("agent_mapping", {}).get(assistant, []) if pack else [],
        "industry_constraints": pack.get("constraints", []) if pack else [],
        "industry_decision_frameworks": pack.get("decision_frameworks", []) if pack else [],
        "industry_artifacts": pack.get("artifacts", []) if pack else [],
        "industry_coverage": INDUSTRY_COVERAGE.get(str(industry).lower(), {}) if industry else {},
        "agent_playbook": AGENT_PLAYBOOKS.get(str(assistant).lower(), AGENT_PLAYBOOKS["saarthi"]),
        "agent_knowledge": knowledge_for(assistant),
    }
