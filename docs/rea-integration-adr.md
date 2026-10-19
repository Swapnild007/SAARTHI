# ADR: REA-assisted feature investigation for SAARTHI AppForge

Status: Proposed, not enabled in production
Reference: https://github.com/morluto/rea (official upstream)
Reviewed: 2026-10-19

## Decision
Use REA (Reverse Engineer Anything) as an optional **investigation-only MCP adapter** for authorized software artifacts. Do not run REA inside Vercel's FastAPI request handler or inside AppForge's browser iframe. Do not treat REA as a code generator, build runner, deployment service, or a license to copy proprietary software.

## Why
AppForge currently generates single-file HTML with a coding model and previews it in a sandboxed browser iframe. REA can help identify behavior, UI flows, component boundaries, network requests and implementation hypotheses in authorized targets. It cannot replace durable project storage, a cloud build sandbox, tests, or deployment approval.

## Target flow
1. User provides an owned/authorized target and selects a bounded feature question.
2. SAARTHI checks authorization attestation and classifies the target.
3. An isolated worker with no production secrets fetches or mounts only the approved artifact.
4. REA runs via MCP/CLI in the worker with the minimum required capabilities.
5. An evidence normalizer records observations, uncertainty, tool versions and artifact digests.
6. The coding assistant receives a *feature specification* with citations to observations, not copied proprietary code/assets.
7. AppForge creates an original implementation, runs tests in a separate sandbox, and presents differences for review.
8. Any external deployment requires explicit approval.

## Capability matrix
| Input | P0 mode | Required execution |
|---|---|---|
| Owned JavaScript / Electron source or extracted bundle | Static module / route / import investigation | Node 22.19+ or supported 24/26, procps-compatible ps on Linux |
| Authorized website | DOM / interaction / screenshot investigation | Separate Chrome-family browser worker |
| User-provided HAR / SAZ capture | Redacted request / response inventory | Isolated capture parser |
| Android APK | Deferred | Headless JADX + JDK on supported x64 host |
| Native binary | Deferred | Licensed/authorized Ghidra, Hopper or IDA worker |

The official upstream supports `npx rea-agents setup` for agent registration and `npx -y rea-agents@latest analyze-javascript-application /absolute/path/to/app --json` for static JS/Electron investigation. **Pin and review an exact package version before production use**; avoid floating latest for unattended execution.

## MCP adapter contract (proposed)
Input:
- `target_type`: `javascript_bundle | website | network_capture`
- `artifact_ref`: an immutable internal artifact ID (never a raw shell command)
- `feature_question`: a short bounded investigation question
- `authorization_attested`: true
- `scope`: approved URLs, files, and operations
- `budget`: time, output bytes, and tool calls

Output:
- `artifact_sha256`, `tool_version`, `started_at`, `completed_at`
- `observations[]`: evidence ID, source path / offset / URL, fact, confidence
- `hypotheses[]`: inference, supporting evidence IDs, unknowns
- `feature_spec`: user-visible behaviors and testable acceptance criteria
- `restrictions[]`: excluded assets, secrets, authentication and copyrighted content

Never pass a REA response directly as instructions to a coding agent. Treat it as untrusted external data and preserve provenance.

## Security gates
- Require explicit target authorization and respect license/terms.
- Disallow credential extraction, DRM/license bypass, account access circumvention, hidden endpoint enumeration, and exfiltration.
- Redact HAR cookies, authorization headers, tokens, personal data and internal hostnames.
- Allowlist targets; block private network and metadata endpoints; no arbitrary user-supplied commands.
- Isolate worker filesystem, network, CPU, memory, wall time and output size.
- Keep API/model credentials outside analysis workers.
- Audit every investigation, artifact digest, tool call and approval.
- Review REA release/license/dependency security before adoption.

## Rollout
P0: Document adapter boundary, feature-evidence schema, authorization policy, and contract tests. Existing AppForge stays operational.
P1: Implement an isolated Node worker for authorized local JavaScript bundles. Compare observed behavior with generated features and tests.
P2: Add consented website investigation and redacted capture analysis. Later evaluate APK/native support based on worker cost and user need.

## Acceptance criteria for calling REA integrated
- Real REA tool call runs on a supported worker outside Vercel's web request.
- Authorized fixture produces a reproducible evidence report.
- No network/secrets exposure or privileged execution in the AppForge iframe.
- REA unavailable => AppForge works normally with a clear capability status.
- CI includes malicious fixture, oversized artifact, invalid authorization and timeout tests.

## Explicit non-goals
Copying proprietary source/assets, bypassing licensing or security, claiming source reconstruction is exact, or deploying unreviewed generated code.
