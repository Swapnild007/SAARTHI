# SAARTHI — Product Architecture

## Product thesis

SAARTHI is an industry-aware intelligence operating system. The seven specialist capabilities are internal execution capabilities, not seven separate products.

**North-star flow**

Understand → Contextualize → Reason → Execute → Verify → Deliver

## Architecture

1. **Intelligence Core** — request understanding, intent classification, conversation continuity, deterministic tools and verification.
2. **Context Engine** — current conversation, selected industry, attachments, locale/timezone and runtime capabilities.
3. **Industry Layer** — vocabulary, workflows, KPIs, constraints, decision frameworks and work-product templates.
4. **Internal Capabilities** — Saarthi, Coding, Research, Create, Data Analyst, Analyze and Plan.
5. **Execution Boundary** — explicit tools and provider routes; no arbitrary code execution.
6. **Work Product Layer** — answers, plans, research briefs, analyses, charts, diagrams and implementation outputs.

## Product principles

- Do not add specialist bots unless a new capability is genuinely required.
- A selected capability changes behavior, not only the label or color.
- When sufficient information exists, act first and state material assumptions.
- Ask questions only when missing information materially changes the result.
- Never fabricate data, sources, tool execution, memory or completed actions.
- Deterministic operations such as time, date, calculation and conversion must execute server-side.
- Conversation history is scoped to the active workspace.
- Industry context must materially affect terminology, workflow, constraints, KPIs and decisions.
- Every meaningful execution should expose a verification step to the user.

## Current maturity focus

### Completed in this iteration

- Industry packs now include constraints, decision frameworks and expected work products.
- Runtime exposes those industry structures to the model.
- Conversation history is now passed to the provider, preserving multi-turn continuity.
- SAARTHI can internally select a specialist capability without forcing a user-facing bot switch.
- Responses expose orchestration metadata for the client.
- The UI now presents the six-stage intelligence pipeline.
- Specialist navigation is framed as internal intelligence capabilities rather than a collection of bots.
- Response metadata identifies an orchestrated workspace.

### Next product layer

- Persistent user/organization memory with explicit controls.
- Real tool execution beyond deterministic system tools.
- First-class artifacts and exportable work products.
- Source-grounded research with citations and retrieval controls.
- Organization-level industry configuration.
- Evaluation harness for routing, hallucination, tool correctness and industry adherence.
- Observability for latency, token usage, failure rate and workflow completion.
- Permissioned integrations and auditable actions.

## Quality bar

SAARTHI should be judged by whether it reliably turns an objective into a useful, verified outcome — not by how many agents appear in the interface.
