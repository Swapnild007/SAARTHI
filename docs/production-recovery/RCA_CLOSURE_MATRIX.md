# RCA closure matrix

| Original finding | Recovery files | Evidence and remaining gate |
| --- | --- | --- |
| `workProductHtml` was commented out and crashed the first render | `index.html`, `scripts/app.js` | Browser first-send assertion checks the user bubble, response and page errors. Render exceptions are isolated from transport. |
| Capture-phase Send script bypassed the transcript | `index.html`, `scripts/app.js` | Browser click/Enter, repeated submit and POST counts. Voice uses the same function. Physical Android keyboard and voice still require an owner-device run. |
| Competing deadlines and misleading success | `backend/app.py`, `backend/engine.py`, `backend/execution.py` | API fixture verifies failure semantics and disconnect. Python subprocess test verifies deadline kill and reap. Provider cancellation beyond SAARTHI's network boundary remains subject to the provider. |
| Goa planning request took 33.49 seconds and cause was unknown | `backend/execution.py`, `backend/engine.py` | New routing, attachment, provider-attempt and persistence measurements. Historical stage remains unknown. |
| Browser history trimmed to 20 messages and swallowed writes | `scripts/app.js` | Browser reopen and backup tests. A conflicting tab is surfaced and refused a destructive overwrite. The losing tab can preserve a backup. |
| CloudStore was never called on chat | `backend/storage.py`, `database/recovery.sql`, `backend/app.py` | HTTP tests reach adapter methods with a fixture. Embedded PostgreSQL verifies migration, ownership predicates, restart persistence, quota, replay and terminal write guards. Live Supabase and secrets remain unavailable. |
| Origin change strands existing browser histories | `scripts/app.js`, deployment runbook | Backup import/export support. Export on the original origin remains necessary prior to an origin migration. |
| Preview pointed at production and CI probed the wrong runtime | `backend/private_session.py`, both workflows, `.python-version` | Cross-origin and wrong-scope fixture tests. Vercel preview reported 3.12.16 and an unconfigured state. A configured preview remains required. |
| Browser IDs were trusted, with missing private access and quotas | `backend/private_session.py`, `backend/app.py`, `database/recovery.sql` | Rotation, unauthorized access, owner separation, body-size, quota and redaction checks. Trusted-edge throttling and provider spending limits still need configuration and verification. |
| Hermes browser secret and unproven continuity | `backend/hermes_bridge.py`, `backend/app.py`, `scripts/app.js` | Tests check server-created session separation, forwarding prior turns and default chat with Hermes disabled. Live gateway and restart evidence remains open. |
