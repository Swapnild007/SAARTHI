# SAARTHI Agent Production Contract

## Purpose

Every SAARTHI agent must satisfy the same minimum contract while retaining its specialist domain behavior.

This contract is the primary checklist for completing the seven agents without prematurely rewriting the backend.

## Required agent definition

Each agent must define:

### Identity
- stable agent ID;
- display name;
- mission;
- scope;
- non-goals.

### Capability
- supported capabilities;
- unsupported capabilities;
- required tools;
- optional tools;
- expected inputs;
- expected outputs.

### Workflow
A deterministic high-level sequence such as:

**understand -> prepare -> execute -> verify -> deliver**

The exact stages may differ by agent.

### Quality gates
Every agent must define measurable checks appropriate to its domain.

### Failure modes
Document:
- bad input;
- missing input;
- ambiguous request;
- unavailable tool;
- provider failure;
- partial result;
- conflicting evidence;
- unsupported request;
- safety boundary;
- verification failure.

### Evidence/provenance
The agent must identify where important results came from.

### Handoff contract
A handoff must communicate:
- objective;
- relevant context;
- completed work;
- unresolved questions;
- artifacts/results;
- verification status;
- constraints.

### Output contract
The output should be:
- directly useful;
- structured when downstream processing is expected;
- explicit about assumptions;
- explicit about uncertainty;
- free of fabricated completion claims.

## Agent-specific acceptance standards

### Saarthi

Must excel at:
- objective understanding;
- automatic capability selection;
- multi-agent coordination;
- context preservation;
- result synthesis;
- verification;
- follow-up state.

Must not:
- pretend a specialist completed work that failed;
- route solely on superficial keywords;
- lose important user constraints during handoff.

### AI Coding

Must cover:
- repository inspection;
- architecture;
- implementation;
- tests;
- debugging;
- refactoring;
- security;
- review;
- deployment readiness.

Must not:
- invent files or test results;
- expose secrets;
- claim deployment without verification.

### Research

Must cover:
- question framing;
- source retrieval;
- source-quality evaluation;
- recency;
- cross-checking;
- contradiction handling;
- synthesis;
- citations.

Must not:
- invent citations;
- treat search snippets as equivalent to primary evidence;
- hide uncertainty.

### Create

Must cover:
- brief interpretation;
- ideation;
- drafting;
- refinement;
- format compliance;
- final artifact validation.

Must not:
- sacrifice factual constraints for style;
- claim an artifact was generated if it was not actually generated.

### Data Analyst

Must cover:
- profiling;
- validation;
- cleaning/reporting;
- metric semantics;
- deterministic calculations;
- statistics;
- KPI intelligence;
- visualization;
- forecasting when supported;
- uncertainty;
- provenance.

Must not:
- fabricate values;
- silently impute;
- incorrectly aggregate rates;
- claim causality from correlation;
- forecast without sufficient evidence.

### Analyze

Must cover:
- evidence extraction;
- pattern detection;
- assumption testing;
- alternative hypotheses;
- root-cause analysis;
- risk;
- tradeoffs;
- confidence and evidence traceability.

Must not:
- turn correlation into causation;
- present a hypothesis as established fact;
- ignore contradictory evidence.

### Plan

Must cover:
- objective;
- decomposition;
- prioritization;
- dependencies;
- owners/resources;
- milestones;
- critical path where applicable;
- risks;
- contingencies;
- execution tracking.

Must not:
- create impossible schedules without identifying constraints;
- hide dependencies;
- present assumptions as confirmed commitments.

## Completion levels

### Level 0: Persona
The agent has a role/prompt but little domain enforcement.

### Level 1: Capability
The agent has explicit capabilities and workflows.

### Level 2: Specialist
The agent has domain knowledge, quality gates and failure modes.

### Level 3: Production
The agent has deterministic/tool-backed execution, provenance and tests.

### Level 4: Industry-ready
The agent works against relevant industry workflows, KPIs, constraints and representative scenarios.

### Level 5: World-ready
The agent is production-observable, secure, resilient, evaluated, provider-aware and globally usable.

## No-backend-first rule

When an acceptance gap is discovered, attempt fixes in this order:

1. existing configuration;
2. knowledge pack;
3. agent capability metadata;
4. playbook/workflow definition;
5. tool configuration;
6. evaluation/test coverage;
7. documentation;
8. backend code only when the runtime cannot satisfy the requirement through the preceding layers.

Every backend change must state:
- the unmet requirement;
- why configuration/knowledge/tests are insufficient;
- the smallest required code change;
- the acceptance test proving the change.

## Current target

The objective is to move all seven agents from their current foundation toward **Level 5**, while keeping the existing backend stable wherever possible.
