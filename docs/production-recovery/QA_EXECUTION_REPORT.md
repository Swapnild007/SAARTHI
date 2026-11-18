# QA execution report

| Layer | Command or environment | Result |
| --- | --- | --- |
| Python regression and HTTP integration | Python 3.12.14, `python -m pytest -q backend tests` | 144 passed, 0 failed, 0 skipped. Starlette emitted one test-client deprecation warning. |
| Real Chromium desktop and Android profile | `SAARTHI_BROWSER_EXECUTABLE=/tmp/chromium npm run test:browser`, Playwright 1.62.1, local Uvicorn, isolated test storage and provider | 8 core browser cases and 2 cancellation cases passed locally. Each profile completed 20 submissions and reopened 40 messages. The suite also covered failure recovery, durable cancellation, CSV attachment/removal, code formatting, thread switching, and backup restore in an empty browser profile. |
| PostgreSQL migration and restart | `node --test tests/database/recovery.test.mjs`, PGlite with a disk-backed temporary database | 1 passed, 0 failed, 0 skipped. Migration applied twice. Role protection, 20 ordered turns after close/reopen, quota, replay, stale reservation and owner-scoped deletion were exercised. |
| Build integrity | `python -m compileall -q backend tests scripts app.py`, `node --check` for browser sources, `python -m pip check`, `git diff --check` | Passed. Local pip-audit reported no known vulnerabilities in the pinned runtime requirements. |
| Vercel preview | `GET /api/health` on the preview built from `f1d77ec0490a7fad72d3f2b943e95b41acb4abd8` | HTTP 200 with `ok:false`, Python 3.12.16, scope unconfigured, provider and persistence unconfigured, Hermes disabled. Vercel build metadata linked the preview to the commit. App-level SHA was null because staging was unconfigured. |

The early CI run failed on a shallow checkout and a fixture selector that hit the backup chooser. Both were corrected. A browser abort-only cancellation trial left a pending turn. The cancellation endpoint now records a durable terminal state. The preinstalled Chromium failed at startup on an unavailable socket. The compatible headless-shell build initially exited between tests when forced into single-process mode. The reported browser results use a full rerun after removing that option. Provider, storage and Hermes fixtures use synthetic data. The headless Android profile covers mobile Chromium behavior and represents a Pixel 7 viewport, touch and user agent. Physical Android Chrome, its keyboard and a real microphone are separate checks.

Open validation includes complete hosted cloud lifecycle, cross-device restore against live Supabase, real provider execution and failure tests, reliable staging deployment/rollback, actual Hermes restart, physical Android voice and orientation, trusted-edge limits, and feature-specific live grading. No production traffic or user data was used during recovery tests.

## Mission 2 validation

- The GitHub API confirmed draft PR #25 at `fcdb7170cc13e4bf56255bead38d47afddd12439` and both jobs passed in baseline run [44085830273](https://github.com/Swapnild007/SAARTHI/actions/runs/44085830273).
- Local Playwright completed 11 cases. One touch-only case was intentionally skipped in desktop Chromium. The added Pixel 7 profile case exercised touch submission and focus, landscape viewport, and a simulated denied microphone permission. Virtual keyboard behavior and physical microphone access require Android hardware.
- Embedded PostgreSQL passed original recovery and new spend admission, credential-role isolation and durable login tests. Python coverage includes scoped credentials, production-fallback refusal, capped and uncapped provider transport contracts, Hermes timeout and permission failure, PostgREST ownership filters and rollback smoke guardrails.
- Vercel returned no branch-scoped environment keys for this recovery branch. Hosted model, Supabase, edge throttle, Hermes and rollback smoke remain blocked. The API and SQL fixture evidence does not certify those integrations.

## Owner setup correction

The owner password dialog previously appeared on deployments without an owner credential. Vercel's environment metadata confirmed no owner variables. New setup uses a Vercel-authenticated helper and a salted scrypt hash. Password recovery preserves owner identity and rotates the session key. Python tests verify hash matching, bad password rejection, reload session checks, expiry, old-session rejection after rotation, malformed configuration and Vercel authorization. The local full Python suite passed 165 tests. The local browser test could not launch either Playwright's absent bundled browser or system Chromium (socket permission denied). CI must execute the added dialog sign-in and reload scenario before browser verification can be claimed. Live chat remains blocked by unconfigured owner, provider and database settings.

## Mobile-only onboarding validation

The local Python suite passed 170 tests. The disk-backed PostgreSQL suite passed three scenarios, including owner authorization expiry, consumption, replay rejection, recovery and permissions. Four targeted wizard browser cases passed across desktop Chromium and the Pixel 7 profile, covering first-time setup, denied management access, password creation, sign-out, reload, chat submission through the fixture, history reopening, recovery and unavailable connections.

An initial browser run hit the shared test server's login throttle across independent scenarios. The fixture now resets its in-process rate bucket at each test boundary. Production limits remain unchanged. The SQL tests verify durable admission and login controls separately.

These browser tests use synthetic management authorization, persistence and model replies. They do not qualify as live owner setup, actual model inference, hosted history, or physical Android evidence. The complete regression workflow runs on each pushed recovery commit and supplies the final PR evidence.

## Live free-provider evidence

[FREE_PROVIDER_LIVE_EVIDENCE.json](FREE_PROVIDER_LIVE_EVIDENCE.json) records three actual OpenRouter replies on the recovery Preview. The responses came from three free models selected by `openrouter/free`. The second response recalled the synthetic marker and the third used the same marker in a sentence. Returned cost was zero for all three calls. Round-trip wall times were 14.34, 6.16 and 5.08 seconds in this single run.

Authenticated session access returned 200. Anonymous conversation access returned 401. Replaying the final turn returned the saved response. A fresh authenticated client read three saved turns, six transcript messages, in paginated order. Synthetic cleanup returned 200. Tests used a five-minute management-authorized diagnostic session and did not require or reset the owner's password. They verify actual authenticated inference and persistence, while a physical Android session remains a separate check.

The initial runtime log query exceeded Hobby retention. A deployment-scoped 15-minute query succeeded and showed the active authenticated requests reading Supabase and, after the fix, reserving and completing turns. Structured terminal logging now includes the turn ID, status, served model and stage times without prompts, replies or API keys.
