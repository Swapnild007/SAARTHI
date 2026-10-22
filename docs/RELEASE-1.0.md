# SAARTHI 1.0 engineering evidence

Issue: [#19](https://github.com/Swapnild007/SAARTHI/issues/19). Branch: `feat/saarthi-1-release`. Date: 22 October 2026 (IST).

**Verdict: NOT production-ready.** Local core journeys and transport tests pass, but live provider inference, hosted MCP, managed execution, physical Android installation/keyboard behavior, and hosted release checks remain open. Do not merge or publicly release on the strength of fixture tests.

Current release-hardening results, corrected Vercel 403 diagnosis, accessibility checks and blockers: [RELEASE-HARDENING.md](RELEASE-HARDENING.md). The original audit below is retained as historical evidence.

## Baseline audit

Default branch inspected at `dd495d0`. No README, JS package manifest, service worker or PWA manifest existed. Backend entrypoints were root `app.py` → `backend/app.py`; FastAPI served static HTML/CSS/JS. Reviewed both requirement files, Vercel/Render configuration, all agent/profile/knowledge modules, attachment/data engines, routes, storage/schema files, RAG and MCP modules, test inventory, workflows and branch history. There was no AGENTS.md.

Reviewed open PR #18 and its `feat/appforge-alpha` branch at `8f5077c`: extensive generation/editing/build/export/project backup, local-provider and SQLite retrieval work already existed. Incorporated that history without merging or closing its original PR. Other open PRs were dependency updates (#10–16); their applicable dependency floors were considered without merging them. Existing backend tests on an isolated unchanged main checkout: **131 passed** (23.34 seconds, rerun from the unchanged-main working directory). Existing JS passed syntax checks. No frontend journey tests existed.

Reproduced/fixed failures beyond those covered by baseline tests:

- An inline capture-phase send handler competed with the real composer, bypassed history and always called the old deployment; it also violated the root script CSP. Removed that duplicate transport.
- A literal `\\n` embedded in a source comment swallowed `workProductHtml`'s declaration. Every conversation render raised a ReferenceError; the send handler swallowed it before making its request.
- Adjacent IIFEs in the AppForge branch lacked a terminating semicolon, raising a startup TypeError despite passing syntax checks.
- Settings opened navigation or informational placeholders. Replaced visible entrypoints with a functional native dialog.
- API routing ignored the current host. Local and branch previews now use their own backend; only the legacy GitHub Pages host uses the existing canonical API.
- Saving/opening history truncated messages to 20; thread/project list caps also silently removed old work. Full local content is retained and context selection is separate.
- Calculator parsing discarded parentheses, failed percentage requests and raised on the bare calculator command. It now returns its own useful input error, never another tool's time result.
- Browser tests caught overlapping navigation/composer controls and a history overlay that stayed open after a thread selection. Both fixed.
- Provider state was shared across requests and fallback metadata could report a different request's route. Selection and diagnostic state are now request-local.
- MCP initialization could fail on valid empty HTTP 202 notifications; sensitive tools could be model-exposed if writes were configured. Fixed the empty response path, argument validation and per-invocation boundary.
- Automatic deployment-wide knowledge retrieval could mix private shared context into anonymous requests. Removed that implicit retrieval; browser excerpts are explicit and permission-controlled.

## Architecture and changes

Preserved the existing Python runtime, deterministic/data/research engines, static frontend, Supabase adapters, SQL schemas and agent knowledge. Integrated AppForge's previous branch instead of replacing it. Added request-local provider selections, real SSE delivery, bounded arithmetic, browser-local knowledge/privacy controls, a unified workspace dialog/navigation, offline utilities and versioned shell caching. The generator's multi-file output is validated before storage/export; static composition happens only inside the existing opaque iframe, with its CSP inserted before all parsed untrusted nodes. Managed builds retain the previous isolated microVM boundary.

New integration points: `backend/provider_settings.py`, `backend/streaming.py`, `backend/calculator.py`, `/api/providers`, `/api/providers/validate`, `/api/command/stream`, `/api/knowledge/extract`, `/api/mcp/invoke`, `scripts/workspace.js`, `scripts/utilities.js`, `styles/workspace.css`, `sw.js`, `manifest.webmanifest`. Existing AppForge, engine, MCP, frontend and CI files are updated. `git diff --name-status origin/main...HEAD` provides the complete consolidated file list, including inherited PR #18 files.

## Feature status

| Feature | Status | Evidence / boundary |
|---|---|---|
| Audit and baseline | Verified | 131 unchanged-main tests; branch/PR/config inspection |
| Settings, model selection, appearance, privacy | Verified | Browser click/save/reload, token non-persistence and API selection tests |
| Gemini/OpenRouter/OpenAI/Groq/Mistral adapters | Implemented but Unverified | Fixed endpoints and per-request model/key routing tested; no live credentials |
| Conversational vendor inference | Blocked | No vendor credentials available for live requests |
| Streaming and provider fallback | Verified | Actual local HTTP provider with SSE and HTTP 429→next-route fallback; not vendor certification |
| Retries, timeouts and rate handling | Verified | Bounded attempts/deadline, explicit rate-limit diagnostics; sensitive actions are not automatically retried |
| Conversation persistence and bounded context | Verified | Browser reload/reopen; history beyond 20 messages retained; latest context plus extractive summary |
| Calculator, time/date boundaries | Verified | HTTP calculator tests and offline parser tests; undefined/unsafe input rejected |
| Browser document ingestion/retrieval/management | Verified | Real file upload, lexical search, reload/storage, consent gate, delete UI; PDF/text extraction API |
| Managed semantic embeddings/pgvector | Implemented but Unverified | Existing dimension-checked adapter/schema retained; database and embedding credentials absent |
| Source-grounded generation | Implemented but Unverified | Selected excerpts reach provider context and source references are exposed; live answer quality not evaluated |
| MCP HTTP initialization/discovery/invocation | Verified | Real local HTTP protocol fixture including 202 notification; not a hosted-connector claim |
| Hosted MCP integration | Blocked | No remote server configuration or credentials supplied |
| Sensitive MCP permissions/schema validation | Verified | Model definitions exclude writes; invalid arguments rejected before HTTP call; manual write confirmation gate tested |
| MCP pagination / OAuth connector onboarding | Not Implemented | Static environment registry and small catalogs only |
| Native AppForge workspace | Verified | Embedded workspace and shared current-tab provider configuration |
| Multi-file generation/validation/export pipeline | Verified | Controlled local HTTP provider returns a real 3-file project; API validation and ZIP contents checked |
| AI-generated application quality | Blocked | Deterministic fixtures do not demonstrate real model output quality |
| Static multi-file preview, file editor, project history | Verified | Browser composes CSS/JS, clicks counter inside sandbox, selects source file; existing checkpoint/export tests |
| Managed isolated dependency execution | Blocked | Vercel credentials/private build key not configured; disabled state verified |
| Full SaaS backend provisioning | Not Implemented | Project generation is not service/account/database provisioning |
| Android responsive navigation | Verified | Chromium touch emulation at 360/393/412 widths, plus tablet/desktop; reduced keyboard viewport checked |
| Physical OPPO/Android keyboard/assistive technology | Blocked | No physical device or TalkBack session available |
| Light theme | Verified | Browser evidence captured |
| Dark/system themes | Implemented but Unverified | Preferences and styles present; complete cross-surface visual/accessibility audit remains |
| Offline application shell/utilities | Verified | Real service worker, offline navigation/reload, calculator and local history/library |
| Actual Android PWA installation | Blocked | Manifest/icons served; install prompt and installed device launch not exercised |
| Production asset validation | Verified | Static asset/JS/Python/manifest validation; this app has no bundler |
| Hosted production runtime / cloud backup | Blocked | No deployment performed; database migration, access control and live cloud persistence require separate validation |
| Dependency audit | Verified | Requirements resolution reports no known vulnerabilities; not a proof of absence of vulnerabilities |
| Public multi-user authentication | Not Implemented | Private deployment token gate only; anonymous session IDs are not accounts |

## Security review

- BYOK secrets are SecretStr-validated and request-local. The browser keeps keys/tokens in memory. API validation drops raw inputs and provider exceptions expose status categories rather than request URLs/keys.
- Endpoints for BYOK providers are fixed, preventing an arbitrary client URL from receiving a key. Existing custom route URLs are administrator-controlled only.
- Managed cloud data and deployment-supplied provider credentials require a private access token and edge controls before exposure. The optional token is not a multi-user authentication service. Existing anonymous session-ID storage must not be advertised as account authentication.
- MCP requires trusted configured servers, exact tool approval, explicit user read permission for chat, and separate confirmed write invocation. Remote schema references, private destinations and redirects are rejected. DNS rebinding and full OAuth interoperability are not independently certified.
- Browser preview has `sandbox="allow-scripts"` without same-origin, plus network-blocking CSP. No user source executes in FastAPI. Package projects cannot claim a preview until built by the isolated service.
- Service worker never caches APIs, document uploads or credentials. Cache migration only removes this app's versioned public shell caches.
- Dependency audit passed. No real credentials were added. Existing public deployment configuration is unchanged; no deployment, merge or database mutation was requested by this work.

## Verification record

- Baseline: `python -m pytest -q /tmp/saarthi-baseline/backend /tmp/saarthi-baseline/tests` → 131 passed (rerun with the unchanged-main worktree as the working directory).
- Integrated suite: `python -m pytest -q backend tests` → **191 passed** (24.29 seconds).
- `npm run build` → asset/syntax/Python compilation checks.
- `npm run test:offline` → arithmetic, safe input and offline fallback.
- `BROWSER_EXECUTABLE=/tmp/saarthi-chrome npm run test:e2e` → real browser journeys; test runner starts its own backend. Downloading Playwright's normal archive failed; a packaged Chromium binary was extracted and used without disabling browser web security.
- `python -m pip_audit -r requirements.txt` → no known vulnerabilities in resolved requirements. This queries the vulnerability database, not source-code risk.
- Screenshots in [evidence](evidence/) show settings, chat, knowledge, AppForge source and desktop layouts. They contain synthetic test data. Fixtures are explicitly labelled in test files.

New CI validates branch assets/backend tests and browser journeys. Removed the old unconditional production smoke step: a branch build must not depend on or exercise a different deployed commit. Hosted smoke validation belongs to the separately approved release process. GitHub-hosted CI results must be checked on this PR; local passes are not CI passes.
