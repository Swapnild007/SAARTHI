# Implementation report

Recovery started from `main` at `dd495d06fed0e3374659177e311794ee780559c6`. The open chat and Hermes drafts were inspected at #22 `323e040`, #23 `c936735` and #24 `6c471bb`. The recovery reuses #22's single composer and truthful timeout direction, #23's mobile composer clearance and conversation styling, and #24's Hermes request contract. The three drafts were left untouched.

| Area | Before | Recovery implementation |
| --- | --- | --- |
| Submission | Renderer threw before fetch. A second script intercepted Send on static hosting. | `index.html`, `scripts/app.js` retain one native form submission and guard. Voice enters through the same submission routine. The user message is saved before transport. Reply storage follows the originating thread even after navigation. |
| Reliability | Multiple browser deadlines and a thread that could continue after a successful-looking timeout result. | `backend/app.py`, `backend/execution.py`, `backend/turn_worker.py` derive an end-to-end budget, terminate and reap the worker, record an explicit terminal state, and replay a reserved turn by ID. Ambiguous failures expose a same-turn retry. |
| History | Context trimming discarded saved messages. Existing storage adapter was disconnected. | `database/recovery.sql`, `backend/storage.py` and the composer reserve the turn before execution. Up to 20 prior model messages come from the authenticated store. Local history remains untrimmed and supports backup export/import. Cloud restoration paginates conversations and individual turns. |
| Hosting | The static controller and work-product page called a hardcoded production endpoint. Preview detection relied on URL patterns. | Same-origin API requests, explicit server environment, expected origin, Vercel environment checks, database scope marker, SHA and Python diagnostics. Static copies can export stored browser history. Switching origins is a separate rollout step. |
| Identity | Browser session identifiers were accepted as ownership. | `backend/private_session.py` issues expiring signed owner cookies. Cloud queries use server configuration for owner scope. New tables use owner-scoped keys and service-role grants. |
| Hermes | Draft bridge accepted a browser-held shared secret. | `backend/hermes_bridge.py` runs behind the same private turn API and derives Hermes session keys from environment, owner and thread. A scope-specific validation flag gates the selector. |
| Release | CI probed production and accepted fallback responses. | PR regression uses isolated fixtures. A separate private smoke checks candidate SHA, environment and Python runtime, exact provider execution, multi-turn recall and cloud history readback. |

## Feature inventory

| Feature | Status and evidence |
| --- | --- |
| Main chat, history, error recovery | Implemented. Browser and API fixture coverage for first send, click/Enter, timeout, thread correlation, 20 sends and 40 messages after reopening. |
| Cloud conversations | Reserved and completed through CloudStore. Read pagination, rename and deletion are API operations. Browser restore is available after sign-in. Live Supabase round trip remains a release gate. |
| Planning, writing, coding and analysis | Existing engine and specialist contracts retained. Unit coverage includes deterministic analysis and routing. Live specialist output quality remains ungraded. |
| Research | Research routing and response contracts retained. External web retrieval through the candidate command worker is disabled pending bounded staging verification. |
| Attachments and charts | Existing readers and chart generation retained with request and attachment restrictions. Browser test sends and removes a CSV and checks code Markdown rendering. PDF, XLSX, and chart correctness have backend coverage. Full browser file-type and chart coverage remains open. |
| Voice | Browser recognition and synthesis remain in the composer. Permission errors are surfaced. A physical microphone permission and recovery run remains open. |
| Retrieval and remote MCP tools | Candidate reports disabled and refuses requests for these integrations. Deterministic date, time, conversion and calculation remain available. |
| Standalone memory | Disabled. Durable conversation context and local backup are provided independently. |
| Automation, tasks, reminders and workflows | Explicit saved-fact writes, task, reminder and workflow commands are disabled until scheduler/storage validation. The notification permission action requests browser permission. |
| Settings, control surfaces and work-product page | Existing controls remain. Work-product requests now use the private same-origin API. Some controls retain informational status only. Separate backend health reports integration availability. |
| Mobile navigation | Existing UI retained with PR #23 clearance and new composer status controls. Chromium mobile emulation and physical Android are tracked separately. |
| Hermes | Server path and controlled response fixtures are implemented. The selector stays hidden in the unconfigured preview. Live gateway mode, outages across restarts and tool containment are independently gated. |

Older messages that were discarded by the old 20-message transcript cap or never written by the inline composer are unavailable through browser backup. Histories still present on an older origin must be exported there before retiring that origin.

Mission 2 added explicit hosted credential scopes, per-owner spend admission and reported-cost recording, durable sign-in limits, live smoke response provenance, and rollback compatibility checks. Hosted standard inference accepts only routes whose upstream key ceiling can be checked. The local OpenAI-compatible route remains available for development. The physical Android checklist and exact staging settings are in the deployment runbook.

## Mobile onboarding

SAARTHI now contains a mobile setup dialog with connection checks, deployment-owner verification, password creation, sign-out and recovery. Owner credentials live in the existing private conversation database when database authentication is enabled. Management verification proves Preview-branch write access against a pinned Vercel project and issues a ten-minute authorization. Password creation consumes that authorization atomically, closes initial setup, and signs the owner in immediately.

The connected Vercel API prepared the recovery branch's Preview settings, including a generated session key. Supabase is available as a plugin but is not connected. Only production-scoped model settings exist. No production credential was copied into Preview and no paid resource was provisioned. Live inference and cloud history remain blocked by those account connections.

## Free-provider recovery

The active Preview's sensitive route variable contained a complete OpenRouter API key by itself. The previous loader accepted only a JSON list and returned an empty list without a diagnostic on parse failure. That produced the user-visible provider-unconfigured error before model execution. The paid-key lifetime-cap check would also have rejected a free route later in execution.

The loader now accepts a complete key only as a documented shorthand for the fixed OpenRouter endpoint and `openrouter/free`. It never extracts a key from a broken JSON document. Valid single-route objects and precisely bounded copy/paste wrappers are normalized, then pass the same endpoint, model, field and fallback checks. Diagnostics report fixed validation-rule names, field names and JSON error positions. They contain no route values or credentials.

For free-only routes, the durable daily turn quota applies without a paid-spend reservation. Requests specify zero input/output provider pricing, omit paid plugins and paid model fallbacks, and reject nonzero or invalid returned cost. Mixed free/paid routes are invalid. Paid-only configurations retain database spend admission and upstream key-cap verification. A single free route has a 14-second provider attempt budget within the existing overall deadline.

The actual authenticated Preview test completed three generated replies with successful recall across turns, an idempotent replay, and six messages restored through pagination in a fresh diagnostic session. All three replies reported zero cost. The verification session was issued through authorized management access for five minutes, using the existing owner credential hash. The owner's password and existing sessions were not changed. Only the synthetic test thread was deleted.
