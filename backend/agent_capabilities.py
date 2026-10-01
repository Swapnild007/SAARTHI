"""Structured capability definitions for SAARTHI's seven specialist agents."""
from __future__ import annotations
from typing import Any

AGENT_CAPABILITIES: dict[str, dict[str, Any]] = {
    "saarthi": {"name":"Saarthi","focus":"general intelligence and orchestration","capabilities":["conversation","decision_support","learning","personal_organization","orchestration"],"workflows":["understand","decide","learn","organize","delegate"],"outputs":["answer","decision_frame","plan","handoff"]},
    "coding": {"name":"AI Coding","focus":"production software engineering","capabilities":["architecture","implementation","debugging","refactoring","testing","code_review","documentation"],"workflows":["inspect","design","implement","test","review","ship"],"outputs":["code","diff","test_plan","architecture","review"]},
    "research": {"name":"Research","focus":"evidence retrieval and synthesis","capabilities":["question_framing","source_evaluation","comparison","synthesis","uncertainty"],"workflows":["frame","retrieve","evaluate","compare","synthesize"],"outputs":["research_brief","comparison","evidence_table","source_notes"]},
    "create": {"name":"Create","focus":"creative production","capabilities":["ideation","writing","editing","storytelling","prompt_design","content_structure"],"workflows":["brief","ideate","draft","refine","finalize"],"outputs":["draft","concept","prompt","outline","creative_direction"]},
    "data_analyst": {"name":"Data Analyst","focus":"quantitative analysis and decision-ready reporting","capabilities":["data_profiling","cleaning_reasoning","statistics","trend_analysis","anomaly_detection","forecasting","visualization"],"workflows":["profile","validate","analyze","visualize","explain"],"outputs":["finding","table","chart","diagram","analysis_brief"]},
    "analyze": {"name":"Analyze","focus":"structured analysis of documents, visuals, systems and situations","capabilities":["evidence_extraction","pattern_detection","risk_analysis","assumption_testing","root_cause","tradeoff_analysis"],"workflows":["scope","extract","test","interpret","conclude"],"outputs":["analysis","risk_register","findings","root_cause","tradeoffs"]},
    "plan": {"name":"Plan","focus":"execution planning and operational strategy","capabilities":["goal_decomposition","prioritization","dependencies","milestones","risk_planning","contingencies"],"workflows":["define","decompose","sequence","validate","execute","review"],"outputs":["roadmap","checklist","timeline","dependency_map","contingency_plan"]},
}

INDUSTRY_PACKS: dict[str, dict[str, Any]] = {
    "travel": {"name":"Travel & Tourism","vocabulary":["destination","itinerary","visa","lodging","transport","budget","seasonality","risk","activities"],"workflows":["destination_research","trip_budget","itinerary","document_checklist","travel_risk_review"],"agent_mapping":{"research":["destination_research","visa_research","travel_requirements"],"data_analyst":["budget_analysis","seasonality_analysis"],"plan":["itinerary","trip_plan","packing_plan"],"create":["itinerary_document","travel_brief"],"analyze":["option_comparison","risk_review"],"saarthi":["trip_orchestration"]},"kpis":["trip_cost","duration","budget_variance","schedule_coverage"]},
    "financial_services": {"name":"Financial Services","vocabulary":["account","transaction","portfolio","cash_flow","risk","compliance","return"],"workflows":["financial_analysis","cash_flow_review","risk_review","reporting"],"agent_mapping":{"research":["market_research"],"data_analyst":["financial_analysis"],"analyze":["risk_review"],"plan":["financial_workplan"],"create":["financial_report"]},"kpis":["revenue","cost","margin","cash_flow","return"]},
    "healthcare": {"name":"Healthcare & Life Sciences","vocabulary":["patient","care_pathway","appointment","clinical_data","outcome","compliance"],"workflows":["care_operations","clinical_research","quality_analysis","capacity_planning"],"agent_mapping":{"research":["clinical_research"],"data_analyst":["quality_analysis"],"analyze":["document_review"],"plan":["capacity_planning"],"create":["patient_education_draft"]},"kpis":["wait_time","capacity","throughput","quality","outcomes"]},
    "retail": {"name":"Retail & E-commerce","vocabulary":["product","inventory","order","conversion","basket","customer","promotion"],"workflows":["sales_analysis","inventory_review","customer_analysis","promotion_review"],"agent_mapping":{"research":["market_research"],"data_analyst":["sales_analysis","inventory_analysis"],"analyze":["customer_analysis"],"plan":["campaign_plan"],"create":["product_content"]},"kpis":["revenue","conversion","average_order_value","inventory_turnover"]},
    "logistics": {"name":"Logistics & Supply Chain","vocabulary":["shipment","route","warehouse","inventory","lead_time","capacity","delivery"],"workflows":["network_analysis","capacity_planning","delivery_review","inventory_review"],"agent_mapping":{"research":["route_research"],"data_analyst":["network_analysis"],"analyze":["root_cause_delivery"],"plan":["capacity_plan"],"create":["operations_brief"]},"kpis":["on_time_delivery","lead_time","fill_rate","capacity_utilization"]},
    "manufacturing": {"name":"Manufacturing","vocabulary":["production","line","downtime","yield","quality","maintenance","capacity"],"workflows":["production_analysis","quality_review","capacity_planning","maintenance_review"],"agent_mapping":{"research":["process_research"],"data_analyst":["production_analysis"],"analyze":["root_cause"],"plan":["capacity_plan"],"create":["operations_report"]},"kpis":["oee","yield","downtime","throughput","defect_rate"]},
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
    }
