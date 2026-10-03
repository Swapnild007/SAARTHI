"""Specialist knowledge pack for SAARTHI's Analyze agent.

Focus: evidence-grounded reasoning across documents, images, systems, incidents and
operational situations. This pack defines analysis method and quality controls,
not model-specific prompts.
"""
from __future__ import annotations

ANALYZE_KNOWLEDGE = {
    "mission": "Turn supplied evidence into a traceable analysis that distinguishes observations, hypotheses, tests, conclusions, risks and actions.",
    "non_negotiables": [
        "Never invent evidence, measurements, document contents, system state or completed checks.",
        "Separate observation from interpretation, hypothesis and conclusion.",
        "A correlation, temporal sequence or co-occurrence is not sufficient to establish causality.",
        "Every material conclusion must be traceable to evidence or explicitly labeled as an assumption or inference.",
        "Actively consider plausible alternative explanations and contradictory evidence.",
        "State what evidence would confirm, weaken or falsify the leading explanation.",
        "Do not hide uncertainty, missing evidence, scope limits or conflicting observations.",
        "For high-impact decisions, stop at analysis and request appropriate human validation when evidence is insufficient."
    ],
    "analysis_contract": {
        "layers": ["source_evidence", "observations", "interpretations", "hypotheses", "tests", "conclusions", "implications", "actions"],
        "evidence_status": ["confirmed", "reported", "inferred", "unknown", "contradicted"],
        "confidence_basis": ["evidence_strength", "source_quality", "coverage", "consistency", "alternative_explanations", "test_results"],
        "causal_standard": [
            "identify temporal ordering",
            "identify plausible mechanism",
            "check confounders and common causes",
            "compare alternatives",
            "seek intervention or quasi-experimental evidence when available",
            "label residual uncertainty"
        ]
    },
    "workflow": [
        "scope_question",
        "inventory_sources",
        "extract_evidence",
        "normalize_entities_and_events",
        "separate_observations_from_interpretations",
        "generate_hypotheses",
        "rank_hypotheses_by_evidence_without_treating_rank_as_truth",
        "test_assumptions",
        "seek_disconfirming_evidence",
        "compare_alternatives",
        "perform_root_cause_or_risk_analysis",
        "state_conclusions_with_confidence",
        "derive_implications_and_actions",
        "verify_traceability"
    ],
    "methods": {
        "root_cause": ["5_whys", "fishbone_categories", "fault_tree", "pareto", "event_timeline", "counterfactual_check"],
        "incident_analysis": ["timeline", "impact_scope", "trigger", "contributing_factors", "control_failure", "containment", "corrective_action"],
        "risk": ["hazard_identification", "likelihood", "impact", "control_effectiveness", "residual_risk", "mitigation"],
        "tradeoff": ["options", "criteria", "constraints", "benefits", "costs", "risks", "reversibility", "unknowns"],
        "document_analysis": ["claim_extraction", "entity_extraction", "table_consistency", "cross_section_check", "missing_clause_review"],
        "visual_analysis": ["object_or_region_identification", "pattern_comparison", "annotation_review", "measurement_if_available", "uncertainty_labeling"]
    },
    "quality_gates": {
        "evidence_gate": ["source_inventory_complete", "material_claims_traceable", "missing_evidence_listed"],
        "reasoning_gate": ["observations_separated", "assumptions_explicit", "alternatives_considered", "contradictions_checked"],
        "causal_gate": ["causal_language_supported", "confounders_considered", "mechanism_not_assumed"],
        "conclusion_gate": ["scope_matches_evidence", "confidence_explained", "uncertainty_visible"],
        "action_gate": ["actions_follow_findings", "high_impact_actions_not_presented_as_authorized", "verification_step_defined"]
    },
    "failure_modes": [
        "confirmation_bias",
        "anchoring_on_first_explanation",
        "correlation_as_causation",
        "post_hoc_reasoning",
        "survivorship_bias",
        "selection_bias",
        "denominator_error",
        "base_rate_neglect",
        "scope_leakage",
        "single_source_overconfidence",
        "silent_missing_data",
        "false_precision",
        "unsupported_root_cause",
        "decorative_analysis_without_decision_relevance"
    ],
    "output_contract": {
        "required_sections": ["question", "evidence", "observations", "hypotheses_or_explanations", "analysis", "conclusion", "uncertainty", "recommended_next_checks"],
        "optional_sections": ["root_cause", "risk_register", "tradeoff_matrix", "timeline", "action_implications"],
        "claim_format": "Material claims should identify supporting evidence and status; inferences must be labeled as such."
    },
    "industry_application": {
        "travel": ["option_comparison", "delay_or_disruption_analysis", "risk_review"],
        "financial_services": ["transaction_pattern_review", "risk_analysis", "cash_flow_anomaly_review", "scenario_tradeoff"],
        "healthcare": ["document_review", "operational_quality_analysis", "safety_risk_review", "care_pathway_analysis"],
        "retail": ["customer_behavior_analysis", "conversion_drop_analysis", "inventory_issue_analysis", "promotion_effect_review"],
        "logistics": ["delivery_exception_analysis", "route_delay_root_cause", "capacity_bottleneck_analysis", "service_level_variance"],
        "manufacturing": ["defect_root_cause", "downtime_analysis", "yield_variance", "quality_incident_review", "process_bottleneck_analysis"]
    },
    "decision_rule": "If evidence is insufficient for a reliable conclusion, produce the strongest bounded finding possible, identify the missing evidence and define the next discriminating check rather than filling the gap with speculation."
}
