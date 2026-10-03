# SAARTHI Data Analyst Agent Knowledge Base

## Purpose

The Data Analyst agent is a quantitative decision-support specialist. It combines deterministic computation with an AI model that handles intent, interpretation, explanation and report composition.

The numerical engine is authoritative for calculations performed on supplied data. The model must not invent values, silently fill missing values, or convert an observed association into a causal claim.

## Production workflow

1. Ingest supplied CSV, spreadsheet, JSON or structured rows.
2. Profile columns, types, missingness, uniqueness and duplicates.
3. Validate data quality and report a quality score plus concrete issues.
4. Clean deterministically without silently changing business meaning.
5. Define metric semantics and aggregation.
6. Calculate descriptive statistics, relationships, outliers and KPI variance.
7. Detect denominator-aware KPIs and use weighted rates where appropriate.
8. Select visualizations from the data shape and analytical question.
9. Forecast only when temporal history is sufficient.
10. Backtest candidate forecasting methods when enough history exists.
11. Explain uncertainty, limitations and coverage.
12. Produce a concise decision-ready answer with traceable findings.

## Analytical coverage

### Descriptive statistics
- Count, sum, mean, median
- Minimum, maximum and range
- Variance and standard deviation
- Quartiles and IQR
- Coefficient of variation
- Approximate 95% confidence interval for a mean
- Z-score extreme-value review
- Distribution skew direction

### Data quality
- Missing-value counts and percentages
- Duplicate-row detection
- Mixed-type detection
- Constant-column detection
- High-cardinality detection
- Row-shape validation
- Numeric/date parsing validation
- Explicit missing-value strategies: report, drop rows, mean, median, mode and forward fill

Imputation is never implicit. A recommendation must be shown before applying a business-impacting missing-value rule.

### Forecasting
The engine supports linear trend, moving average, exponential smoothing, seasonal naive, holdout model selection using MAPE, and residual-based uncertainty bands.

The engine reports the selected method, history length, validation approach and limitations. Forecasts are predictive estimates, not causal explanations.

### KPI intelligence
- Additive metrics such as volume, units and revenue
- Average/rate metrics such as AHT, ASA, conversion and service levels
- Lower-is-better metrics such as cost, defects, downtime, waiting and abandonment
- Higher-is-better metrics such as revenue, throughput, yield and service level
- Target variance and target attainment
- Weighted numerator/denominator rates for common operational KPIs

Examples of denominator-aware metrics include conversion, abandon rate, defect rate, yield and on-time delivery.

## Visualization intelligence

The engine supports 15 chart families: bar, line, pie, donut, scatter, bubble, area, stacked bar, histogram, box, radar, funnel, gauge, waterfall and heatmap.

The chart is selected because it answers an analytical question, not because it is visually attractive.

## AI platform knowledge

The specialist knowledge layer is informed by public documentation from OpenAI, Google Gemini, Anthropic Claude, xAI, OpenRouter, pandas, scikit-learn, statsmodels, Microsoft Power Query, Microsoft Power BI/DAX, Tableau, and Hugging Face Datasets/Evaluate.

See backend/data_analyst_knowledge.py for the versioned source registry and execution rules.

## Separation of responsibilities

**AI model**
- Understand the question
- Identify the analytical objective
- Identify appropriate engine operations
- Explain results
- Surface assumptions and limitations
- Produce a decision-ready narrative

**Deterministic engine**
- Parse and validate data
- Calculate metrics
- Build chart specifications
- Detect quality problems
- Run statistical calculations
- Run forecast models and backtests

This separation reduces hallucinated arithmetic and makes the agent testable.

## Current architecture

attachment -> data profile -> validation -> cleaning -> deterministic analysis -> visualization/forecast -> AI interpretation -> response

The agent remains provider-neutral. The configured OpenAI-compatible gateway can route to different model providers while the deterministic analyst contract remains unchanged.