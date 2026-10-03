# SAARTHI World-Ready Standard

## Purpose

SAARTHI is being developed as a production-grade, multi-agent AI platform rather than as a certification project or a collection of seven prompts.

This document defines the acceptance standard for the product. It is intentionally implementation-neutral where possible so that existing backend behavior is preserved until a code change is demonstrably necessary.

## Engineering principle

**Configuration, knowledge, contracts, tests, documentation and evaluation come before backend rewrites.**

A backend change is justified only when:
1. the requirement cannot be expressed through existing configuration, knowledge, tools, prompts, schemas or tests;
2. the current runtime produces an objectively incorrect or unsafe result;
3. the change has a defined acceptance test; and
4. the change preserves existing supported behavior unless the requirement explicitly changes it.

## World-ready dimensions

### 1. Agent intelligence

All seven agents must have:
- a precise mission;
- explicit scope and boundaries;
- capability definitions;
- workflow/playbook;
- quality gates;
- failure modes;
- required inputs;
- expected outputs;
- escalation/handoff rules;
- uncertainty behavior;
- evaluation cases.

Agents:
1. Saarthi: orchestration and general decision support
2. AI Coding: software engineering
3. Research: evidence engineering
4. Create: content and artifact production
5. Data Analyst: quantitative decision support
6. Analyze: evidence and problem analysis
7. Plan: execution and operational planning

### 2. Agent orchestration

SAARTHI must be able to:
- identify the user's objective;
- select one or more capabilities;
- execute specialists in sequence or parallel when appropriate;
- preserve context across handoffs;
- validate specialist results;
- recover from a failed specialist;
- avoid duplicate work;
- return one coherent user-facing result.

Routing must be objective-driven, not persona-driven.

### 3. Industry intelligence

Initial supported industries:
- Travel & Tourism
- Financial Services
- Healthcare & Life Sciences
- Retail & E-commerce
- Logistics & Supply Chain
- Manufacturing

Each industry pack must define:
- vocabulary;
- business entities;
- workflows;
- KPIs;
- constraints;
- decision frameworks;
- agent mappings;
- artifact bundles;
- risk/compliance considerations;
- representative evaluation scenarios.

The architecture must permit additional industries without rewriting the seven agents.

### 4. Tool and integration layer

Tools must be treated as controlled capabilities with:
- explicit schemas;
- input validation;
- permission boundaries;
- timeout/retry behavior;
- deterministic result handling where applicable;
- provenance;
- error reporting;
- safe failure.

Target integration classes:
- web/research;
- files;
- code execution;
- data analysis;
- GitHub/software engineering;
- MCP;
- business APIs;
- artifact generation.

### 5. Knowledge and model independence

SAARTHI must not depend on one model vendor.

The agent contract should remain stable while models/providers can be changed or routed according to:
- task;
- capability;
- quality;
- latency;
- cost;
- availability;
- context requirements.

Provider-specific behavior belongs behind a provider/model boundary.

### 6. Memory and state

The product must distinguish:
- conversation context;
- task state;
- agent execution state;
- user preferences;
- durable memory;
- artifact state.

Memory must have:
- provenance;
- relevance controls;
- update rules;
- privacy boundaries;
- deletion/retention behavior;
- conflict handling.

The system must never imply that information was remembered or retrieved when it was not.

### 7. Evaluation

Evaluation is a first-class product capability.

Every agent needs:
- happy-path cases;
- ambiguous cases;
- boundary cases;
- adversarial cases;
- tool failure cases;
- missing-data cases;
- regression cases;
- industry-specific cases.

Evaluate at minimum:
- correctness;
- task completion;
- groundedness;
- tool correctness;
- schema correctness;
- citation/provenance integrity;
- safety/guardrail compliance;
- latency;
- cost;
- recovery behavior.

### 8. Guardrails and governance

Guardrails must exist at four levels:
1. input;
2. tool/action;
3. model output;
4. final delivery.

Sensitive or irreversible actions require explicit authorization where appropriate.

The system must enforce:
- least privilege;
- secret isolation;
- data minimization;
- auditability;
- safe failure;
- human approval for high-impact actions.

### 9. Observability

Production execution should be diagnosable without exposing secrets.

Track, where appropriate:
- request/run ID;
- selected agent;
- industry;
- routing decision;
- tool calls;
- model/provider route;
- latency;
- token/cost metadata;
- failures;
- retries;
- fallback;
- verification status;
- artifact/result references.

### 10. Reliability

Production behavior must define:
- timeout;
- retry;
- fallback;
- partial completion;
- degraded mode;
- duplicate prevention;
- idempotency where actions exist;
- recovery after tool/provider failure.

No failure path should silently become a fabricated success.

### 11. Global readiness

SAARTHI should support:
- timezone-aware behavior;
- locale-aware formatting;
- currency and unit handling;
- multilingual user interaction;
- regional date formats;
- country/region-specific constraints;
- explicit uncertainty when local rules are unknown or stale.

Global readiness does not mean claiming legal, medical, financial or regulatory authority. The product must distinguish information from professional advice and use appropriate escalation boundaries.

### 12. Artifact quality

Generated artifacts must be:
- structurally valid;
- complete for their requested format;
- traceable to source data/evidence;
- internally consistent;
- appropriately named;
- safe to share;
- validated before being reported as complete.

### 13. Security

Minimum security posture:
- no secrets in source;
- environment-based credentials;
- least-privilege tools;
- authenticated access for protected operations;
- authorization before sensitive actions;
- input validation;
- output validation;
- prompt/tool injection resistance;
- audit logging;
- dependency/security checks.

### 14. Performance and cost

SAARTHI should route work according to required quality rather than always using the most expensive model.

Track:
- latency;
- model/provider availability;
- token usage;
- estimated cost;
- tool execution time;
- retry overhead;
- cache opportunities.

### 15. Deployment readiness

The product must eventually have:
- reproducible builds;
- environment separation;
- health checks;
- configuration validation;
- CI;
- automated tests;
- deployment verification;
- rollback strategy;
- runtime observability.

## Release gates

A capability is not considered production-ready merely because it produces a plausible answer.

### Gate A: Functional
The capability works for its defined supported scope.

### Gate B: Evidence
Important claims/results have traceable provenance.

### Gate C: Reliability
Known failures are handled without silent fabrication.

### Gate D: Security
Permissions, secrets and high-impact actions are controlled.

### Gate E: Evaluation
Automated tests cover normal, edge and failure cases.

### Gate F: Operational
The capability is observable, diagnosable and deployable.

### Gate G: Industry
Relevant industry workflows, KPIs, constraints and artifacts are tested.

## Definition of World-Ready

SAARTHI reaches the world-ready milestone only when every supported agent and industry passes the applicable release gates.

Certification is a separate outcome. Certifications can validate external knowledge, but they do not define SAARTHI's engineering standard.
