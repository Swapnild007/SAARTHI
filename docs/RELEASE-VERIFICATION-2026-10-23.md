# Release verification — 23 October 2026

Verdict: **BLOCKED — not production-ready**. Authoritative feature gates and continuation commands: [completion status](../SAARTHI_COMPLETION_STATUS.md).

## Implemented in PR #20

- Added a bundled Capacitor Android app, Kotlin allowlisted device bridge, scoped document import/export, Android Keystore preference encryption, native speech and WorkManager reminders.
- Added browser voice language, transcript synchronization, stop/interruption and mute controls. Late recognition callbacks cannot submit after cancellation.
- Added reminder review UI, recurring/due status, local persistence, reconnection/focus recovery and cross-tab delivery locks. Daily briefings are reminders to request a briefing, not unattended research.
- Added explicit preference/project memory with independent sharing consent, review/search and deletion.
- Added bounded MCP catalog pagination, malformed/cyclic catalog/schema rejection and fresh permission checks after cached discovery.
- Fixed Devanagari combining-mark tokenization in browser and SQLite retrieval. Small lexical evaluation returns the correct first source for four fixtures across English/Hindi/Marathi.
- Fixed compiled AppForge previews: selected output-root CSS/JS is inlined; unsafe/missing assets, code-split modules and media-dependent output are explicitly unavailable. Package builds require a dist/build entry; unsupported output never becomes a raw-source preview.
- Preserved original chat, providers, specialized engine, history, knowledge, AppForge and web identity. Android icons use existing SAARTHI assets.

## Evidence boundaries

Local Python: 225 tests. Node capabilities: 11 tests. Existing browser journeys exercise Settings, tab-only credentials, history, calculator, document lifecycle, AppForge executable preview/edit/restore/export, offline recovery and layout widths. Six new screen/theme axe scans plus ten existing scans have zero serious/critical findings. Screenshots and JSON under `docs/evidence/` are browser evidence, not photographs of a physical Android device.

Real provider, hosted MCP, managed RAG/database and managed Sandbox credentials are absent. Controlled fixtures are labeled and do not certify external inference, generated expense-app quality or remote execution.

The local headless Chromium 131 confirms manifest validity, service-worker control and zero installability errors, but lacks the CDP `PWA.install` command. Full Chromium CI [run 39877382486](https://github.com/Swapnild007/SAARTHI/actions/runs/39877382486) installed and launched the PWA successfully on `978d19e`; [browser artifact](https://github.com/Swapnild007/SAARTHI/actions/runs/39877382486/artifacts/12468293772). Physical Android install remains unverified.

Android debug build first passed at `864eda8` in [run 39877088246](https://github.com/Swapnild007/SAARTHI/actions/runs/39877088246), including JVM reminder rules. The final implementation `978d19e` also built successfully in [run 39877382341](https://github.com/Swapnild007/SAARTHI/actions/runs/39877382341), job 120166203818: `BUILD SUCCESSFUL in 2m 23s`; [APK/JVM report artifact](https://github.com/Swapnild007/SAARTHI/actions/runs/39877382341/artifacts/12467894493). The downloaded report confirms **3 JVM tests, 0 failures**. Android apksigner verifies the debug APK signature; package `com.saarthi.assistant`, min SDK 23 / target SDK 35. APK SHA-256: `7bb7f5bb55ad529f8cd1342b4d5bf8777deb20418094cf1e574ae8e100dd90e8`. The APK contains no backend origin or backend source files. Native device execution and emulator instrumentation remain separate gates.

## Focused security review

Reviewed boundaries: API access/body limits and conversation ownership from the preserved hardening work; request-local provider configuration; document bounds; memory consent/rendering; MCP discovery/schema/allowlist/write-revocation behavior; AppForge source/output paths, sandbox CSP and build execution separation; native package allowlist, permission requests, scoped files, Keystore, logging, backup, cleartext and WebView frame isolation.

Repaired this session: cached MCP permissions could remain usable until the discovery cache expired; invocation now checks the current allowlist/write permission, with regressions. Native AppForge untrusted frames must never use Capacitor's legacy JavascriptInterface fallback; that fallback is removed and a modern WebView is required. Compiled project output is never represented by source HTML when the build preview is unavailable.

Dependency evidence: npm audit reports zero known vulnerabilities; pip-audit reports zero known vulnerabilities among 43 resolved Python dependencies. No secret values were printed or committed. This is focused review and regression evidence, not an exhaustive formal security certification. The Codex security-scan skill's required preflight resource/tools were unavailable, so no formal security-scan report or absence-of-vulnerabilities claim is made. Manual review, physical Android testing and deployment egress/access controls remain release gates.

## External checks

- Vercel management project lookup returned HTTP 403: connection lacks scope `swapneeldalvi3-1192`. This does not prove an application failure or deployment protection. No scope/protection setting was changed.
- The existing branch preview `/api/health` returned HTTP 200 and `provider_configured:false`, managed persistence/MCP/RAG unconfigured. It predates these changes; no hosted-head verification is claimed.
- Real public DeepWiki discovery returned zero tools because the public-destination guard rejected this environment's DNS result. No invocation or guard bypass: [record](evidence/hosted-mcp-current.json).
- Local Java outbound requests could not resolve Gradle/Maven downloads through this execution network. Actual native builds/tests therefore run in GitHub CI; no local APK or local emulator claim.

No new pull request, merge, public deployment, payment or database migration was performed.

Emulator verification initially failed before test execution because unqualified Gradle installation tasks also built dependency-library test applications with conflicting Kotlin dependencies. Workflow repair `0709799` targets `:app:installDebug` and `:app:installDebugAndroidTest`; the corrected run is a separate gate.

Application commit `dbde615` adds the Android online-without-backend calculator recovery. It built successfully, and API 35 instrumentation returned **OK (3 tests)** for packaged startup/native network/local calculation, encrypted preference lifecycle, and reminder persistence/delivery/deduplication/cancellation. [APK/JVM artifact](https://github.com/Swapnild007/SAARTHI/actions/runs/39878323589/artifacts/12469407542) · [Instrumentation output](https://github.com/Swapnild007/SAARTHI/actions/runs/39878323589/artifacts/12469163570). The job failed only afterward because the runner lacks rg; the assertion now uses Python. The corrected workflow must be green before claiming all CI checks passed. Latest APK: 13,217,444 bytes, SHA-256 `2a5e3386df873904e87518e7d0e59dc729b722abc4530f938b97c9b014daa210`.
