# Production readiness

**NO-GO. Evidence score: 43% (6 of 14 gates).** Each named acceptance gate has equal weight. A gate earns one point when its required behavior has direct test evidence at the relevant layer. An open or partially verified gate earns zero. Local fixture results qualify for functional browser and API behavior. Hosted infrastructure gates require hosted evidence. The score measures gate coverage and makes no reliability prediction.

| Gate | Result | Evidence or required closure |
| --- | --- | --- |
| Chat submission | Pass | Clean first send and zero page errors on the Chromium scenarios. |
| Duplicate requests | Pass | Exact browser POST counts plus API and SQL replay tests. |
| Message delivery | Pass | 20 sends and 40 ordered local transcript messages on each browser profile. |
| Conversation history | Open | Local restore and SQL persistence passed. Verify hosted cloud readback and cross-device restore. |
| Timeouts | Pass | Server terminal error, disconnect, real subprocess teardown, and browser recovery. |
| Authentication | Pass | Local protected operations, signed session rotation, owner-scoped reads and writes. |
| Environment isolation | Open | Same-origin code and mismatch tests pass. Prove a configured preview cannot use production resources. |
| CI | Open | Workflows added. Required checks and private smoke must pass on the release SHA. |
| Android | Open | Emulation passed. Verify physical keyboard, permissions, rotation and touch on Android Chrome. |
| Desktop | Pass | Core chat, history, attachments and failure recovery passed in Chromium. |
| Persistence | Open | Embedded PostgreSQL restart passed. Rehearse hosted DB recovery and terminal-turn replay from staging. |
| Hermes | Open, disabled | Live gateway continuity, restart and tool scope are unverified. |
| Security | Open | Configure and verify edge controls, budgets, data retention and isolated hosted secrets. |
| Rollback | Open | Run the staging rehearsal against a compatible private release. |

GitHub Actions and Vercel preview builds alone do not authorize release. Keep hosted chat fail-closed until the private staging origin, owner, model provider and cloud store are configured. Keep Hermes, remote tools, retrieval and standalone memory disabled until their gates are addressed.
