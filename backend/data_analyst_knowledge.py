"""Production knowledge pack for SAARTHI Data Analyst.

This file stores distilled, public-practice guidance. It is not model weights,
private prompts, proprietary datasets, or copied training material.
"""

from __future__ import annotations

DATA_ANALYST_KNOWLEDGE = {
    "mission": "Turn supplied data into reproducible, decision-ready analysis with explicit data-quality and uncertainty controls.",
    "operating_rules": [
        "Use supplied data as the numerical source of truth.",
        "Never fabricate, silently impute, or silently discard business data.",
        "Profile before calculating: schema, types, missingness, duplicates, cardinality, ranges and temporal coverage.",
        "Run deterministic calculations in code; use the language model for intent, interpretation and explanation.",
        "Choose aggregation from metric semantics. Counts and additive measures can be summed; rates and averages normally require weighted or denominator-aware treatment.",
        "Do not treat correlation as causation. Flag confounding, selection bias and time trends when relevant.",
        "Forecasts are estimates, not facts. Report history length, validation method, model choice and uncertainty.",
        "Separate data quality findings, statistical findings, business KPI findings and recommendations.",
        "Keep provenance from source field to calculation to finding to chart.",
        "For large datasets, state coverage limits and avoid pretending that a bounded sample is the complete dataset.",
    ],
    "pipeline": [
        "ingest",
        "profile",
        "validate",
        "clean_or_explicitly_report",
        "define_metric_semantics",
        "calculate",
        "validate_calculations",
        "visualize",
        "interpret",
        "forecast_if_supported",
        "explain_uncertainty",
        "deliver",
    ],
    "quality_gates": {
        "data": [
            "column names are understood",
            "data types are plausible",
            "missing values are quantified",
            "duplicates are quantified",
            "date coverage is understood",
            "numeric parsing failures are surfaced",
        ],
        "statistics": [
            "sample size is adequate for the requested method",
            "outliers are identified without automatic deletion",
            "association is not presented as causation",
            "confidence intervals carry method limitations",
            "forecast backtesting is used when enough history exists",
        ],
        "visuals": [
            "visual has a defined analytical purpose",
            "axes and units are explicit",
            "aggregation matches metric semantics",
            "visual does not imply unsupported precision",
            "dashboard prioritizes the decision rather than decoration",
        ],
    },
    "methods": {
        "descriptive": ["count", "sum", "mean", "median", "min", "max", "range", "variance", "standard_deviation", "quartiles", "IQR", "coefficient_of_variation"],
        "relationships": ["Pearson_correlation", "ranked_comparison", "group_comparison", "weighted_average"],
        "quality": ["missingness", "duplicates", "mixed_types", "constant_columns", "high_cardinality", "IQR_outliers", "z_score_review"],
        "forecasting": ["naive", "moving_average", "exponential_smoothing", "linear_trend", "seasonal_naive", "holdout_model_selection", "residual_intervals"],
        "kpi": ["target_variance", "target_attainment", "weighted_rate", "volume", "rate", "cost", "margin", "throughput", "conversion", "yield", "service_level"],
    },
    "chart_selection": {
        "bar": "category comparison or ranking",
        "line": "time or ordered trend",
        "area": "magnitude over an ordered dimension",
        "stacked_bar": "composition across categories",
        "scatter": "relationship between two numeric variables",
        "bubble": "relationship plus a third magnitude dimension",
        "histogram": "distribution of a numeric variable",
        "box": "distribution, spread and outlier comparison",
        "heatmap": "matrix across two dimensions",
        "funnel": "sequential conversion or attrition",
        "waterfall": "positive and negative contributions to a total",
        "pie": "simple part-to-whole with few categories",
        "donut": "simple part-to-whole with a center KPI",
        "radar": "small-number multi-dimensional profile comparison",
        "gauge": "single bounded KPI where a meaningful target/range exists",
    },
    "ai_platform_patterns": {
        "OpenAI": [
            "Use model reasoning for task framing and interpretation, but use deterministic tools for numerical computation.",
            "Use file-aware/code-execution workflows for spreadsheet or tabular analysis when the provider route supports them.",
            "Use structured tool outputs when the application needs machine-readable analysis artifacts.",
        ],
        "Google Gemini": [
            "Use Python code execution for calculations, transformations and graph generation when available.",
            "Use file input for CSV/text analysis and inspect execution results before explaining them.",
            "For agentic workflows, keep code execution, filesystem and web access behind explicit tool boundaries and validation.",
        ],
        "Anthropic Claude": [
            "Use explicit tool definitions and structured tool results for actions.",
            "For long data-rich prompts, keep source data clearly separated from the question and instructions.",
            "Use verification steps after tool execution rather than trusting narrative output alone.",
        ],
        "xAI Grok": [
            "Use structured outputs when downstream analysis needs a schema.",
            "Combine tool calling with structured output when the workflow needs external data plus predictable machine-readable results.",
        ],
        "OpenRouter": [
            "Keep SAARTHI's provider-neutral analyst contract stable while allowing model routing and fallback.",
            "Use structured tool-calling patterns so the deterministic analysis engine remains independent of the selected model.",
            "Record the active route/model in operational telemetry without exposing credentials.",
        ],
    },
    "analytics_stack": {
        "pandas": "Tabular ingestion, cleaning, grouping, joins, reshaping and time-series manipulation.",
        "scikit_learn": "Preprocessing, model evaluation, transformations and machine-learning metrics.",
        "statsmodels": "Statistical models, diagnostics and time-series methods.",
        "Power_Query": "Import and reshape data with repeatable transformations.",
        "Power_BI_DAX": "Semantic-model calculations, measures and query-driven reporting.",
        "Tableau": "AI-ready data modeling, field semantics, visualization and dashboard design.",
        "Hugging_Face": "Dataset discovery and evaluation resources for ML/AI experiments.",
    },
    "failure_modes": [
        "averaging percentages that should be weighted",
        "summing a rate or average as though it were additive",
        "forecasting with too little history",
        "extrapolating a trend through a structural break",
        "deleting outliers without domain review",
        "filling missing values without declaring the imputation rule",
        "using a chart because it looks good rather than because it answers a question",
        "claiming causality from correlation",
        "mixing synthetic demonstration values with real user data",
        "hiding a bounded-data limitation",
    ],
    "sources": [
        {"name": "OpenAI API documentation", "url": "https://platform.openai.com/docs/", "purpose": "model, tool, file and code-assisted workflows"},
        {"name": "Google Gemini code execution", "url": "https://ai.google.dev/gemini-api/docs/code-execution", "purpose": "Python execution, file analysis and graph generation"},
        {"name": "Google Gemini agents", "url": "https://ai.google.dev/gemini-api/docs/agents", "purpose": "managed agent, code, file and web workflow patterns"},
        {"name": "Anthropic Claude documentation", "url": "https://docs.anthropic.com/", "purpose": "tool use, long-context and agentic workflow patterns"},
        {"name": "xAI structured outputs", "url": "https://docs.x.ai/developers/model-capabilities/text/structured-outputs", "purpose": "schema-constrained analysis outputs"},
        {"name": "OpenRouter", "url": "https://openrouter.ai/learn", "purpose": "provider-neutral routing, tool calling and agent architecture"},
        {"name": "pandas documentation", "url": "https://pandas.pydata.org/docs/", "purpose": "tabular analysis and data preparation"},
        {"name": "scikit-learn documentation", "url": "https://scikit-learn.org/stable/user_guide.html", "purpose": "preprocessing, transformations and evaluation"},
        {"name": "statsmodels documentation", "url": "https://www.statsmodels.org/stable/", "purpose": "statistical models and time-series analysis"},
        {"name": "Power Query documentation", "url": "https://learn.microsoft.com/en-us/power-query/", "purpose": "repeatable data preparation and transformation"},
        {"name": "Power BI DAX documentation", "url": "https://learn.microsoft.com/en-us/power-bi/transform-model/desktop-quickstart-learn-dax-basics", "purpose": "semantic-model calculations and measures"},
        {"name": "Tableau Agent best practices", "url": "https://help.tableau.com/current/online/en-us/web_author_einstein_best_practice.htm", "purpose": "AI-ready data modeling, field semantics and calculated fields"},
        {"name": "Hugging Face Datasets", "url": "https://huggingface.co/docs/hub/en/datasets", "purpose": "dataset discovery and dataset cards"},
        {"name": "Hugging Face Evaluate", "url": "https://huggingface.co/docs/evaluate/index", "purpose": "evaluation methodology and metrics"},
    ],
}


def data_analyst_knowledge() -> dict:
    return DATA_ANALYST_KNOWLEDGE
