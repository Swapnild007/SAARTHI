# QA execution report

| Layer | Command or environment | Result |
| --- | --- | --- |
| Python regression and HTTP integration | Python 3.12.14, `python -m pytest -q backend tests` | 143 passed, 0 failed, 0 skipped. Starlette emitted one test-client deprecation warning. |
| Real Chromium desktop and Android profile | `SAARTHI_BROWSER_EXECUTABLE=/tmp/chromium npm run test:browser`, Playwright 1.62.1, local Uvicorn, isolated test storage and provider | 8 passed, 0 failed, 0 skipped on the final run. Each profile completed 20 submissions and reopened 40 messages. The suite also covered failure recovery, CSV attachment/removal, code formatting, thread switching, and backup restore in an empty browser profile. |
| PostgreSQL migration and restart | `node --test tests/database/recovery.test.mjs`, PGlite with a disk-backed temporary database | 1 passed, 0 failed, 0 skipped. Migration applied twice. Role protection, 20 ordered turns after close/reopen, quota, replay, stale reservation and owner-scoped deletion were exercised. |
| Build integrity | `python -m compileall -q backend tests scripts app.py`, `node --check` for browser sources, `python -m pip check`, `git diff --check` | Passed. Dependency vulnerability scanning is configured in CI and tracked separately. |
| Vercel preview | `GET /api/health` on the preview built from `f1d77ec0490a7fad72d3f2b943e95b41acb4abd8` | HTTP 200 with `ok:false`, Python 3.12.16, scope unconfigured, provider and persistence unconfigured, Hermes disabled. Vercel build metadata linked the preview to the commit. App-level SHA was null because staging was unconfigured. |

The preinstalled Chromium failed at startup on an unavailable socket. The compatible headless-shell build initially exited between tests when forced into single-process mode. The reported browser results use a full rerun after removing that option. Provider, storage and Hermes fixtures use synthetic data. The headless Android profile covers mobile Chromium behavior and represents a Pixel 7 viewport, touch and user agent. Physical Android Chrome, its keyboard and a real microphone are separate checks.

Open validation includes complete hosted cloud lifecycle, cross-device restore against live Supabase, real provider execution and failure tests, reliable staging deployment/rollback, actual Hermes restart, physical Android voice and orientation, trusted-edge limits, and feature-specific live grading. No production traffic or user data was used during recovery tests.
