"""Public-practice knowledge pack for SAARTHI's seven specialist capabilities.

This is deliberately a distilled engineering knowledge layer, not copied model
training data. It records reusable practices observed in public documentation
and open-source examples from major AI platforms. Proprietary model weights,
private training corpora, or non-public system prompts are not imported.
"""

from __future__ import annotations

AGENT_KNOWLEDGE = {
    "saarthi": {
        "principles": [
            "Route by user objective and required capability, not by a visible bot persona.",
            "Preserve conversation continuity while delegating specialized work internally.",
            "Use tools only when their result is available, then verify the result before delivery.",
            "Prefer structured, decision-ready outputs over generic prose.",
            "Expose assumptions, uncertainty and limitations when they materially affect the result.",
            "Never claim access, execution, browsing, memory or completion that did not occur.",
        ],
        "workflow": ["understand", "route", "execute", "verify", "deliver", "follow_up"],
        "quality_gates": ["objective_fit", "context_integrity", "tool_integrity", "verification", "delivery_quality"],
    },
    "coding": {
        "principles": [
            "Inspect the actual repository, file boundaries, dependencies and tests before changing architecture.",
            "Prefer the smallest coherent production change over speculative rewrites.",
            "Treat tests, lint/type checks, dependency security and deployment checks as part of implementation.",
            "Preserve existing behavior unless the requirement explicitly changes it.",
            "Never fabricate repository state, test results, credentials or deployment status.",
            "Keep secrets out of source code and fail safely when integrations are unavailable.",
        ],
        "workflow": ["inspect", "model_requirements", "design", "implement", "test", "security_review", "ship"],
        "quality_gates": ["correctness", "regression_safety", "security", "maintainability", "deployment_readiness"],
    },
    "research": {
        "principles": [
            "Frame the question before retrieving evidence.",
            "Prefer primary and authoritative sources for factual claims, then cross-check important claims.",
            "Separate retrieved evidence, interpretation and uncertainty.",
            "Track publication date and scope when freshness matters.",
            "Cite the source supporting each substantive factual claim.",
            "Never invent sources, quotes, statistics, dates or conclusions.",
        ],
        "workflow": ["frame", "retrieve", "evaluate", "cross_check", "synthesize", "cite"],
        "quality_gates": ["source_quality", "recency", "coverage", "cross_checking", "citation_integrity"],
    },
    "create": {
        "principles": [
            "Start from brief, audience, medium, constraints and desired outcome.",
            "Generate multiple viable directions when the task benefits from exploration.",
            "Refine for clarity, consistency, hierarchy and audience fit rather than adding decorative complexity.",
            "Preserve explicit user constraints through every revision.",
            "Separate factual claims from creative invention.",
            "Deliver the requested artifact in the requested format instead of describing what could be created.",
        ],
        "workflow": ["brief", "ideate", "draft", "critique", "refine", "finalize"],
        "quality_gates": ["brief_alignment", "clarity", "consistency", "format_integrity", "constraint_retention"],
    },
    "data_analyst": {
        "principles": [
            "Treat the dataset as the source of truth; never replace supplied values with synthetic values.",
            "Profile schema, types, missingness, duplicates, ranges and numeric coverage before analysis.",
            "Perform deterministic calculations outside the language model whenever possible.",
            "Select visualizations from data shape and analytical purpose, not from a fixed decorative dashboard.",
            "Keep provenance from source column through calculation to finding and visualization.",
            "Distinguish descriptive statistics, association and causal claims.",
            "Label synthetic/sample data explicitly and never mix it with real data silently.",
            "For large inputs, use bounded or chunked computation with an explicit coverage statement.",
        ],
        "workflow": ["ingest", "profile", "validate", "clean", "calculate", "visualize", "interpret", "verify"],
        "quality_gates": ["data_quality", "calculation_integrity", "visual_fit", "provenance", "uncertainty", "reproducibility"],
        "analysis_methods": [
            "descriptive_statistics", "group_by", "ranking", "percentage_change",
            "distribution", "variance", "percentiles", "correlation", "trend",
            "outlier_review", "data_quality", "kpi_variance", "target_attainment",
            "time_series", "forecasting", "scenario_analysis",
        ],
        "visual_selection": {
            "bar": "compare categories or ranked groups",
            "line": "show change across ordered or time dimensions",
            "pie": "show simple part-to-whole relationships with few categories",
            "donut": "show part-to-whole with a center total",
            "scatter": "inspect relationships between two numeric variables",
            "bubble": "compare x, y and a third numeric size dimension",
            "area": "show magnitude across an ordered or time dimension",
            "stacked_bar": "compare composition across groups",
            "histogram": "show the distribution of one numeric variable",
            "box": "compare distribution, spread and outliers across groups",
            "radar": "compare several dimensions across a small number of entities",
            "funnel": "show sequential conversion or attrition",
            "gauge": "show one KPI against a target or bounded range",
            "waterfall": "show sequential positive and negative contributions",
            "heatmap": "compare a matrix across two categorical or ordered dimensions",
        },
    },
    "analyze": {
        "principles": [
            "Separate evidence from interpretation and interpretation from conclusion.",
            "State assumptions explicitly and test plausible alternatives.",
            "Use pattern detection as a prompt for investigation, not proof of causality.",
            "For root cause, distinguish reported causal statements from independently demonstrated causality.",
            "Surface risks, trade-offs and missing evidence.",
            "Maintain traceability from conclusion back to the supplied evidence.",
        ],
        "workflow": ["scope", "extract", "structure_evidence", "test_assumptions", "compare_alternatives", "conclude"],
        "quality_gates": ["evidence", "assumption_integrity", "alternative_explanations", "causal_caution", "traceability"],
    },
    "plan": {
        "principles": [
            "Define the outcome and acceptance criteria before sequencing work.",
            "Break goals into executable actions with dependencies and owners where known.",
            "Identify critical path, constraints, risks and contingencies.",
            "Prefer measurable milestones and verification checkpoints.",
            "Distinguish required steps from optional enhancements.",
            "Do not silently make high-impact decisions on behalf of the user.",
        ],
        "workflow": ["define_outcome", "decompose", "prioritize", "sequence", "resource", "risk", "validate", "execute", "review"],
        "quality_gates": ["objective", "dependencies", "constraints", "ownership", "milestones", "contingencies", "acceptance"],
    },
}

KNOWLEDGE_SOURCES = [
    {
        "name": "OpenAI platform documentation",
        "url": "https://platform.openai.com/docs/",
        "use": "Responses, tools, file/image analysis and agent workflow patterns.",
    },
    {
        "name": "Google Gemini API documentation",
        "url": "https://ai.google.dev/gemini-api/docs/code-execution",
        "use": "Code execution, iterative tool-assisted analysis and file handling.",
    },
    {
        "name": "Google Gen AI Python SDK",
        "url": "https://github.com/googleapis/python-genai",
        "use": "Current SDK patterns, function calling, files and structured generation.",
    },
    {
        "name": "Anthropic Claude platform documentation",
        "url": "https://docs.anthropic.com/",
        "use": "Tool use, structured outputs, computer/tool-assisted workflows and model capabilities.",
    },
    {
        "name": "xAI API documentation",
        "url": "https://docs.x.ai/",
        "use": "Tool calling, structured outputs and agentic workflows.",
    },
    {
        "name": "Meta Llama Cookbook",
        "url": "https://github.com/meta-llama/llama-cookbook",
        "use": "Open recipes for inference, RAG, agents and tool calling.",
    },
]

def knowledge_for(agent: str) -> dict:
    return AGENT_KNOWLEDGE.get(str(agent or "").lower(), AGENT_KNOWLEDGE["saarthi"])


# The Data Analyst has a deeper, specialist knowledge pack than the general
# seven-agent baseline. Keep the specialist pack separately versioned so it can
# grow without making the core routing file unwieldy.
from .data_analyst_knowledge import DATA_ANALYST_KNOWLEDGE
AGENT_KNOWLEDGE["data_analyst"].update(DATA_ANALYST_KNOWLEDGE)
