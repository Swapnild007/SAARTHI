# SAARTHI · सारथी

Personal AI workspace: conversation, private browser history, document context, optional remote MCP tools, and AppForge creation. This branch prepares **1.0**; it is not a production-readiness claim. See [release evidence and outstanding gates](docs/RELEASE-1.0.md).

## Native Android and release status

See [completion gates](SAARTHI_COMPLETION_STATUS.md), [Android build and device checks](docs/ANDROID.md), and [current verification report](docs/RELEASE-VERIFICATION-2026-10-23.md). Voice/device, Automation and Personal memory are available from Settings. Browser reminders require SAARTHI to remain open; Android reminders use WorkManager and may be delayed.

## Run

Python 3.12+ and Node 22+ for validation/browser tests:

```bash
python -m pip install -r requirements.txt
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`. There is no JavaScript bundler or compilation step for serving the app. `npm run build` validates the shipped static assets, JavaScript syntax, Python compilation and manifest.

## Providers and privacy

Settings supports Gemini, OpenRouter, OpenAI, Groq and Mistral through their OpenAI-compatible endpoints. Enter the **exact model ID from your provider console**; model availability and free-tier quotas change. Key/model validation queries the selected provider's model listing; it does not prove successful inference. A provider key is sent over HTTPS to this backend and onward to its fixed provider endpoint. It stays in browser memory for the current tab, not localStorage, cookies, a URL, conversation context, or the service worker. Re-enter it after reload. API validation errors omit raw inputs.

For deployment-wide routes retain `SAARTHI_LLM_ROUTES_JSON`, or the existing `SAARTHI_LLM_API_URL`, `SAARTHI_LLM_API_KEY`, `SAARTHI_LLM_MODEL` variables. Routes must be administrator-controlled. Optional local model settings are documented in [LOCAL_AI.md](docs/LOCAL_AI.md). Provider fallback to a deployment route requires a Settings opt-in for BYOK requests. Defaults configured on the backend retain their ordered route behavior. Attempts are bounded; no automatic retry of sensitive tool writes occurs. HTTP 429 failures are surfaced rather than hidden.

**Private hosting:** set a strong `SAARTHI_ACCESS_TOKEN`; enter it in Settings for the current tab. It gates all API paths except health. Do not expose a deployment containing service credentials or cloud-stored personal data without access control and edge rate limiting. This is a personal deployment gate, not multi-user identity or tenant authentication. Do not publish a shared account service using anonymous session IDs.

## Knowledge

Upload TXT, Markdown, CSV, JSON or PDF in Knowledge. Text documents are indexed in this browser; PDF extraction is stateless on the backend (first 20 pages, no OCR). Uploads are limited to 500 KB, indexed text to 100,000 characters per document, and the local library to 20 documents / 1.5 million characters. The browser uses overlapping chunks and lexical retrieval. Enable explicit knowledge sharing in Settings to send matching excerpts with a question. Source titles/chunk references appear with the answer. Retrieved material is untrusted evidence, never tool instructions; source presence does not independently fact-check a model's claims.

Managed embeddings/pgvector APIs and the SQLite backend index remain available behind `SAARTHI_KNOWLEDGE_ADMIN_TOKEN`; see [RAG-MCP-SETUP.md](docs/RAG-MCP-SETUP.md). The browser library is separate from that administrator collection. Anonymous chat never silently retrieves deployment-wide documents. Serverless local SQLite is not durable storage: use the browser library or managed storage instead.

## MCP

Remote Streamable HTTP endpoints are configured through `SAARTHI_MCP_SERVERS_JSON`. Credentials come from named backend environment variables; tools require an exact allowlist. In Settings → Tools & MCP, enter the knowledge/MCP admin token to discover tools and inspect schemas. Chat additionally needs the read-only permission toggle. Even if server configuration permits writes, sensitive tools are excluded from model definitions. Manual invocation requires review and confirmation each time. Arguments are schema-validated; external schema references, private destinations and redirects are blocked. A tool's read-only annotation is a hint from the server: approve only tools/endpoints you trust.

Real HTTP protocol tests use a controlled local fixture, including initialization, 202 notifications, discovery, session headers, schema rejection, invocation and write confirmation. **No hosted remote connector has been certified in this environment.** Connector pagination and OAuth account linking are remaining compatibility work; connect small statically configured tool catalogs for now.

## AppForge

Build opens inside the SAARTHI workspace and uses the current tab's provider configuration. Clear creation requests from chat transfer their requirements into AppForge. The generator requests a plan and multi-file JSON project; validates path, file-type, size and manifest limits; and supports source editing, local checkpoints, restoration and ZIP export. Static local CSS/JS files are composed into a preview with an opaque sandbox origin and network-blocking CSP. Runtime JavaScript errors are reported to the workspace. Package-dependent projects show a managed-build requirement instead of an unbuilt preview.

Existing safe starter fallback is explicitly labelled when a model cannot produce valid code. It is not a completed application. No SQL, authentication, payments or server integration is invented or provisioned by that fallback. Managed execution uses the existing optional Vercel Sandbox adapter; it requires credentials and `APPFORGE_BUILD_TOKEN`, and is disabled otherwise. See [AppForge setup](docs/appforge-alpha.md). No generated code executes in the trusted API process. Live managed execution and a real SaaS backend are not certified by local preview tests.

## Offline and data

Installability is provided by the manifest and public service worker shell cache. After an online first load, history, local text knowledge search, AppForge source editing and arithmetic/time/date work offline. Cloud inference, PDF extraction, remote MCP and cloud builds require connectivity. No on-device LLM is bundled. Time/date use the device clock offline.

API responses, uploads and credentials are never cached by the worker. Activation removes only previous `saarthi-shell-*` caches; conversations/documents/preferences are not worker caches and survive updates. New workers wait for existing clients to close, avoiding a forced mid-session upgrade. Browser history retains complete threads; only the latest 20 messages plus a bounded extractive summary of earlier user context are sent to the backend. Individual provider requests further bound recent messages. Storage can fill; export important conversations and projects. Settings exposes export, credential forgetting, and confirmed conversation deletion. Document deletion is per document with confirmation.

## Verify

```bash
npm ci
npm run build
npm test
npm run test:offline
npx playwright install --with-deps chromium
npm run test:e2e
python -m pip install pip-audit
python -m pip_audit -r requirements.txt
```

The E2E runner starts its own local backend. `BROWSER_EXECUTABLE=/path/to/chromium npm run test:e2e` supports an existing browser binary. Browser generation fixtures and local HTTP protocol fixtures are explicitly distinguished from live vendor tests in the release report. No production deployment or database migration is performed by these commands.
