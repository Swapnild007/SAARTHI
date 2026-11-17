# Production readiness

**NO-GO. 6 of 14 gates passed (42.86%, rounded to 43%).** Passed gates divided by 14, multiplied by 100. Blocked, failed and partially verified gates earn zero. Hosted and device criteria require their respective environments.

| Gate | Status | Evidence | Environment | Outstanding action | Owner dependency |
| --- | --- | --- | --- | --- | --- |
| Chat submission | PASS | First send, scoped response and Chromium exception assertions in recovery regression. | Local / CI | — | No |
| Duplicate requests | PASS | Exact POST count, API same-turn retry and PostgreSQL replay. | Local / CI | — | No |
| Message delivery | PASS | 20 sends and 40 ordered browser messages after reopen in both profiles. | Local / CI | — | No |
| Conversation history | BLOCKED | Browser backup and restore, SQL restart, paginated adapter contract. | Local / CI | Run 16+ real turns and reopen the paginated transcript in a fresh session on isolated staging. | Yes |
| Timeouts | PASS | Worker termination and reaping, browser cancellation and recovery, typed gateway timeout fixtures. | Local / CI | — | No |
| Authentication | PASS | Private owner cookie tests, rotation, authenticated endpoint and denied cross-owner access. | Local / CI | — | No |
| Environment isolation | BLOCKED | Scoped credentials, pinned Supabase project, missing config and mismatch tests. | Local / CI / Preview | Configure separate staging resources. Verify exact deployment SHA and a successful staging-only smoke. | Yes |
| CI | BLOCKED | Backend, browser and SQL regression workflows exercised. | CI | Run the credentialed private candidate smoke against the approved SHA. | Yes |
| Android | BLOCKED | Chromium Pixel 7 profile, touch, landscape viewport and simulated permission-denied handler. | Local / CI | Run the physical-device checklist in Android Chrome. | Yes |
| Desktop | PASS | Chromium chat, history, attachments and recovery. | Local / CI | — | No |
| Persistence | BLOCKED | Disk-backed embedded PostgreSQL restart, ownership, replay, deletion and adapter scope checks. | Local / CI | Apply migration to isolated Supabase, restart a compatible staging backend and verify restoration and replay. | Yes |
| Hermes | BLOCKED | Server-only gateway credentials, scoped session, disabled tools requirement and typed fixture failures. | Local / CI | Optional feature. Provide a restricted staging gateway and verify continuity, restart and failure before enabling. | Yes |
| Security | BLOCKED | Durable login limits, owner quota, spending reservations and upstream key-ceiling validation. | Local / CI | Apply login rate limiting at the isolated Vercel edge. Verify separate secrets, actual provider cap, and staging retention and deletion. | Yes |
| Rollback | BLOCKED | Approved-origin and SHA guards, synthetic compatibility rehearsal in the private smoke workflow. | Local / CI | Supply two compatible staging builds. Switch staging traffic, run the evidence procedure, and record the restored SHA and transcript. | Yes |

Hermes remains an independently gated optional integration. The original scoring denominator includes its gate. Default chat still has mandatory hosted and device blockers.
