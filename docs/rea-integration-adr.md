# REA adoption policy for SAARTHI

## Decision
Initial REA use is internal-only: analyze SAARTHI's own source and explicitly authorized fixtures in CI. Do not expose arbitrary target analysis to AppForge users in Alpha.

## First integration
The workflow `.github/workflows/rea-self-analysis.yml` pins `rea-agents@6.7.0`, runs the upstream JavaScript application analyzer against the checked-out SAARTHI source, and uploads the JSON evidence report for seven days. It is triggered by relevant pull requests or manually.

## How findings may be used
- Identify existing frontend modules, entry points, imports, and architectural boundaries.
- Turn supported findings into an original implementation plan and testable acceptance criteria.
- Keep evidence references and unknowns attached to the report.
- Review results before using them to change AppForge.

## Guardrails
- Only analyze code SAARTHI owns or has explicit permission to inspect.
- Treat analyzer output as untrusted data, never as instructions or proof by itself.
- Do not extract credentials, bypass access controls/DRM, or copy proprietary source/assets.
- Pin the tool version and review package provenance before updating it.
- This workflow is analysis only. It does not publish a deployment, modify source files, or install a persistent service.

## Next gate
After the workflow succeeds on SAARTHI's source, define a small typed evidence schema and connect reviewed findings to AppForge planning. A user-facing target upload feature is deferred until authentication, quotas, artifact isolation, and a separate managed execution worker are implemented.
