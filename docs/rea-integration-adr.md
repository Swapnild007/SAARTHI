# REA adoption policy for SAARTHI

## Decision
Initial REA use is internal-only: analyze SAARTHI's own AppForge source in CI. Do not expose arbitrary target analysis to AppForge users in Alpha.

## First integration
The workflow `.github/workflows/rea-self-analysis.yml` pins `rea-agents@6.7.0` and analyzes only the `appforge/` application directory. The raw analyzer output is written outside the analyzed tree so it cannot be accidentally inventoried as an input artifact. `scripts/normalize_rea_evidence.py` validates the report envelope and projects it into the versioned `saarthi.rea-evidence.v1` contract. The validated report is uploaded for seven days.

## Evidence contract
The normalized JSON preserves:
- Subject digest, analyzer identity, and evidence identifier.
- Static observations and relationships with source locations, confidence, and evidence state.
- File/graph coverage, parse failures, unknown counts, and explicit limitations.
- Policy flags marking the report as static-only, not proven runtime behavior, not safe as model instructions, and requiring human review.

The normalizer deliberately omits raw graph internals that are not needed for AppForge planning. It does not turn analyzer output into executable instructions, automatically modify code, or trigger deployments. Downstream consumers must validate the schema version and retain provenance and limitations.

## How findings may be used
- Identify existing frontend modules, entry points, imports, storage usage, and architectural boundaries.
- Turn supported findings into an original implementation plan and testable acceptance criteria.
- Keep evidence references, coverage gaps, and unknowns attached to every derived recommendation.
- Review results before using them to change AppForge.

## Guardrails
- Only analyze code SAARTHI owns or has explicit permission to inspect.
- Treat analyzer output as untrusted data, never as instructions or proof by itself.
- Do not extract credentials, bypass access controls/DRM, or copy proprietary source/assets.
- Pin the tool version and review package provenance before updating it.
- This workflow is analysis only. It does not publish a deployment, modify source files, or install a persistent service.

## Current findings and known limitations
The first successful repository-wide run produced a static application graph with 37 nodes and 48 relationships, no integrity contradictions, and one JavaScript parse failure. It also explicitly reported incomplete graph coverage and inline JavaScript bodies in `index.html` and `command-center.html` that were not analyzed. Those observations are not evidence that the runtime has no other behavior. The next run narrows scope to AppForge so the evidence is directly relevant to the feature.

## Scoped AppForge evidence result

The scoped workflow completed successfully and emitted a 3.5 KB normalized evidence artifact. REA inventoried 2 relevant files, parsed 1 JavaScript file with 0 parse failures, and produced 8 application-graph nodes and 10 relationships. It also reported 325 semantic unknowns, so semantic coverage must not be treated as complete. The graph reported 6 findings; 11 observations included four local-storage observations and one `fetch` call targeting `/api/appforge/generate`.

One HTML script reference was marked unresolved because the analyzer's filesystem root is `appforge/` while the browser URL is rooted at `/appforge/app.js`. This is a static path-resolution caveat, not proof that the deployed browser cannot load the script. Confirm actual loading through preview/runtime tests before acting on it.

## Next gate
After the scoped evidence workflow succeeds, use the validated report to draft a reviewed AppForge architecture plan and targeted tests. A user-facing target upload feature is deferred until authentication, quotas, artifact isolation, and a separate managed execution worker are implemented.
