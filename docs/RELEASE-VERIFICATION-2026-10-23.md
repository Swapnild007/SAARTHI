# Release verification — 23 October 2026

Verdict: **BLOCKED — not production-ready**. Full feature gates and exact continuation commands: [completion status](../SAARTHI_COMPLETION_STATUS.md).

Application implementation: `dbde6150a74bdca0c87aa9f380570b044b35bfcc`. Android workflow verified at `b624069`; browser workflow verified at `a43b4b4`. Later evidence-only commits do not change the application implementation.

## Result

The existing unified assistant, providers, history, knowledge, MCP and AppForge are preserved. Added a bundled Capacitor/Kotlin Android app, constrained device operations, scoped document import/export, Keystore preference encryption, native speech interfaces and WorkManager reminders. Added multilingual browser voice controls, explicit preference/project memory and reminder review/status/cancellation/recovery. No always-listening or offline-AI claim.

Repaired MCP catalog pagination/schema/cycle handling and cached permission revocation; Devanagari combining-mark retrieval; compiled AppForge asset previews; Android utility routing when online without a configured backend; native main-frame isolation; and CI SDK/module/browser/result-check portability.

## Verified evidence

| Check | Status | Result |
|---|---|---|
| Python | VERIFIED | 225 tests; baseline 202 |
| Node capabilities | VERIFIED | 11 tests, including native export byte preservation/cancellation/limit |
| Native JVM | VERIFIED | 3 tests, 0 failures |
| Android API 35 instrumentation | VERIFIED | 3 tests: packaged startup/native network/local calculation, encrypted preference lifecycle, reminder persistence/delivery/deduplication/cancellation |
| Android debug APK | VERIFIED | Build and signature checks; package com.saarthi.assistant; min SDK 23, target SDK 35 |
| Browser journeys | VERIFIED | Settings/history/tab-only secrets, calculator, knowledge lifecycle, executable AppForge fixture/edit/restore/ZIP, offline recovery, 360/393/412/768/1440 widths and 450px keyboard viewport |
| Accessibility | VERIFIED | 16 screen/theme axe scans, zero serious/critical findings; manual TalkBack remains unverified |
| Lexical retrieval fixture evaluation | VERIFIED | Expected first source in 4/4 English/Hindi/Marathi fixtures; not semantic/model-grounding certification |
| PWA | VERIFIED | Chrome 155.0.8059.39 installed and launched in an ephemeral CI profile; offline shell/manifest/installability checks pass |
| Dependencies | VERIFIED | npm: zero known vulnerabilities; pip-audit: 43 resolved dependencies, zero known vulnerabilities |

[Android build and tests](https://github.com/Swapnild007/SAARTHI/actions/runs/39878950499) · [Debug APK/JVM report](https://github.com/Swapnild007/SAARTHI/actions/runs/39878950499/artifacts/12469477707) · [Native instrumentation output](https://github.com/Swapnild007/SAARTHI/actions/runs/39878950499/artifacts/12469717312) · [Browser/PWA run](https://github.com/Swapnild007/SAARTHI/actions/runs/39879800138).

Verified APK: 13,217,444 bytes. SHA-256: `8d872aff8d43309bf562ec64c55b05d0cba0ff2a2a7c9fecabc6ccdc403c99f3`. It is debug-signed and contains no backend origin or backend source. Configure an approved backend/CORS/access gate before Android cloud chat; see [Android guide](ANDROID.md).

The native reminder test moves a persisted fixture's due time before invoking delivery. It proves the native persistence/delivery/deduplication/cancellation code path, not natural elapsed-time delivery under doze/reboot/force-stop or a physical manufacturer's battery policy. Physical Android camera, location, app intents, speech, system file picker and notification tray behavior remain IMPLEMENTED BUT UNVERIFIED.

Browser provider, speech and project-generation fixtures are controlled and labeled. They do not certify actual vendor inference or managed build execution. Screenshots are browser emulation, not physical-device photographs. Local Chromium 131 lacks PWA.install; the separate Chrome 155 CI run supplies actual installation evidence.

## Security review

Reviewed boundaries: preserved API access/body limits and conversation ownership; request-local provider configuration; document bounds; memory consent/rendering; MCP discovery/schema/allowlist/write-revocation behavior; AppForge source/output paths, sandbox CSP and execution separation; native package allowlist, scoped files, Keystore, permissions, logging, backup, cleartext and WebView frame isolation.

Repaired cached MCP permissions that could remain usable until discovery expiry: invocation now checks current allowlist/write permission, with regressions. Removed Capacitor's legacy JavascriptInterface fallback because untrusted AppForge frames require modern main-frame message handling. The emulator verifies the supported bridge actually works. Compiled output never becomes a raw-source preview when output/assets are unavailable.

Known credential-pattern review of tracked UTF-8 source found no matches. No provider secrets were printed or committed. This is focused review, regression and dependency evidence, not an exhaustive security certification. The Codex security-scan skill's required preflight resource/tools were unavailable; no formal scan or absence-of-vulnerabilities claim is made. Managed execution, deployment egress/access controls and manual physical-device review remain gates.

## External dependencies and unfinished scope

- BLOCKED: Real Gemini/OpenRouter responses, managed Sandbox builds, semantic RAG/embeddings and database persistence: credentials/configuration unavailable.
- BLOCKED: Real hosted MCP discovery/invocation. DeepWiki returned zero tools because this environment's DNS result fails the public-destination guard; no invocation or bypass. [Record](evidence/hosted-mcp-current.json).
- BLOCKED: Vercel management API returns 403 for scope swapneeldalvi3-1192. Existing preview health returns 200 with provider/persistence/MCP unconfigured; that preview predates this code. No new deployment is authorized or verified.
- IMPLEMENTED BUT UNVERIFIED: Actual speech services/language packs and the physical Android matrix in ANDROID.md.
- NOT IMPLEMENTED: MCP OAuth onboarding, cloud scheduled/general multi-step workflows, always-listening wake word, offline AI model and public multi-user identity. Daily briefing reminders prompt the user to request a briefing; they do not run unattended research.

No new PR, merge, public deployment, paid provisioning or database migration was performed. Continue on draft PR #20; remaining P0 acceptance gates are explicit in the completion file.
