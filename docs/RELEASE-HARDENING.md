# PR #20 release hardening — 22 October 2026 UTC

**Verdict: keep draft; not production-ready.** This report supplements the original implementation audit in [RELEASE-1.0.md](RELEASE-1.0.md). Main is preserved. No new PR, merge, paid resource provisioning or manual deployment was performed. Branch auto-deploy is disabled in `vercel.json` for `feat/saarthi-1-release`; enabling a deployment is a separate approval step.

## Repaired blockers

- GitHub's previous Release journeys run [39785560890](https://github.com/Swapnild007/SAARTHI/actions/runs/39785560890) failed at the offline percentage calculator after reload. A browser can retain `navigator.onLine === true` while requests fail. Transport failures now use the explicit offline utility router; HTTP/provider/auth errors remain errors. The browser regression deliberately forces the stale online hint while disconnected and requires `15% of 200` → `30`.
- Shell cache v2 canonicalizes asset URLs with query strings and returns an explicit offline response for unavailable optional resources. API calls, mutations, credentials and documents are excluded from caching.
- Shared deployment providers, cloud stores or MCP configuration now fail closed unless private deployment access is configured. Conversation writes check ownership before appending messages; malformed conversation IDs cannot enter PostgREST filters. This remains a private deployment gate, not multi-user account authentication.
- Request bodies are limited before parsing, including chunked requests without Content-Length. Rate identity storage is bounded; forwarded identity headers are trusted only with explicit proxy configuration. CORS wraps early error responses and permits the actual DELETE method.
- Package builds require an explicit nonempty build script, including safe rejection of malformed script containers; an absent script can no longer pass via `--if-present`.
- AppForge cloud merge and project navigation preserve browser projects beyond 30 and retain equal-version local checkpoints. AppForge now follows light/dark/system preferences, improves text contrast and focus indicators, invalidates stale build artifacts on edits, and includes private access headers on capability/project reads. Internal dialog navigation retains the original focus target.
- Embedded AppForge’s Back link closes its parent workspace without nesting the home page or reloading in-memory credentials.
- Mobile AppForge retains visible New project and operation feedback controls; nested workspace overflow is checked at Android widths.
- Settings exposes the browser's install prompt when available and explains the unsupported state. Installation is not simulated.

## Local verification

| Check | Result |
|---|---|
| Python backend + integrations | **202 passed**, 27.06 seconds |
| Production build | Passed static asset validation, all JavaScript syntax, Python compilation, manifest checks; this architecture has no bundler |
| Offline unit checks | Passed arithmetic, bounds, routing and honest unavailable-cloud behavior |
| Real Chromium browser journeys | Passed Settings/save/forget, model preferences, memory-only secrets, conversation export, calculator HTTP routing/history/reload/long history, knowledge upload/search and confirm/cancel deletion, MCP authorization rejection, AppForge editing/restore/export, offline shell/calculator and recovery |
| AppForge static execution | Actual 3-file fixture composed in an opaque `allow-scripts` iframe; counter clicked, JS edited and executed, checkpoint restored; real backend ZIP downloaded and all three archive members checked |
| Mobile layouts | Touch/mobile emulation at 393×852; overflow checks at widths 360, 393, 412, 768, 1440; composer fits reduced 450px viewport |
| Accessibility | Axe WCAG A/AA/2.1 AA scan of ten screen/theme states; zero serious/critical findings; [machine-readable results](evidence/accessibility.json) |
| PWA | Real service worker control, manifest, zero installability errors, offline shell; **installed and launched** in full Chromium 151 on GitHub CI, ephemeral regular profile |
| Dependency vulnerability review | `npm audit --omit=optional`: 0 vulnerabilities; `python -m pip_audit -r requirements.txt`: no known vulnerabilities |

Browser version locally: Chromium 153.0.8010.0. The packaged headless binary was needed because the standard archive could not be downloaded in this environment. No browser web-security disabling flag was used. Screenshots contain synthetic data. Width/viewport emulation does not certify a physical Android keyboard, TalkBack, OS safe areas or actual Android installation.

The ten accessibility states are home light/dark, Settings light/dark, tools/MCP, knowledge, chat, history, AppForge light/dark. Automated scanning is not a complete manual accessibility certification. Other legacy tools and external-service controls have not all passed a live end-to-end run.

`PWA.install` is absent in the local headless-shell binary; [local PWA evidence](evidence/pwa.json) records that limitation. Full Chromium 151 on GitHub CI **successfully installed and launched** the app in an ephemeral regular profile, then uninstalled it. [CI browser run](https://github.com/Swapnild007/SAARTHI/actions/runs/39817746893), job `119960578503`, records the successful protocol calls. This passes desktop installation in CI, not physical Android installation.

## Vercel 403 diagnosis

The connected management request `GET /v13/deployments/dpl_2L9dmZCBVmKnehhRKQXkKHdWqKaV?teamId=team_3MuR4IdlZbN0hBYFxpJIw5pf` returns **403 forbidden: not authorized under scope `swapneeldalvi3-1192`**. It reports `saml:false`, `ssoEnforced:false`. This is a Vercel **control-plane access failure**. The suggested team-authorization operation is not exposed in this environment; no authorized CLI token is present. Build/runtime logs and deployment metadata remain inaccessible.

Ordinary unauthenticated HTTPS requests to the existing [branch preview](https://saarthi-git-feat-saarthi-1-release-swapneeldalvi3-1192.vercel.app) succeed without cookies, tokens, special headers, share URLs or a protection bypass. Health, MCP status, AppForge health, calculator (`60`) and ZIP export returned HTTP 200. The earlier inference that management 403 meant a protected application is corrected: **these runtime checks do not encounter deployment protection**. This does not establish the protection policy for every deployment or endpoint.

This is the **existing preview before the new hardening changes**, not a hosted verification of the new branch head. [Hosted HTTP evidence](evidence/hosted-runtime.json) records results. It reports no deployment provider, MCP or managed build configuration, and a non-writable local knowledge database. These are actual application configuration limitations, distinct from management API access.

Reproduce non-destructively:

```bash
curl -i 'https://saarthi-git-feat-saarthi-1-release-swapneeldalvi3-1192.vercel.app/api/health'
curl -i 'https://saarthi-git-feat-saarthi-1-release-swapneeldalvi3-1192.vercel.app/api/command' \
  -H 'Content-Type: application/json' --data '{"message":"calculate (12 + 8) * 3"}'
```

If a different URL presents a protection/login page, stop and obtain authorized access; do not add a bypass.

## External integrations and remaining gates

| Feature | Status | Exact boundary / unblock |
|---|---|---|
| Gemini/OpenRouter live inference and streaming | **Blocked** | No relevant credential values configured locally; existing preview reports provider_configured=false. Configure credentials through the secure deployment/environment or current-tab Settings, then validate and send real requests. No paid request was made. |
| Other provider adapters/fallback | **Implemented but Unverified** for vendor inference | Local real HTTP/SSE/rate-limit fixtures pass, but do not certify vendor models. |
| Hosted MCP discovery | **Blocked** | Attempted public no-auth `https://mcp.deepwiki.com/mcp`, allowlist `read_wiki_structure`; destination fails the existing public-address guard in this network. Zero tools discovered. Guard was preserved. [Evidence](evidence/hosted-mcp.json). |
| Hosted MCP permission/execution | **Blocked** | Discovery did not complete, so no remote execution claim. Local protocol, schema, allowlist and confirmation tests remain Verified. Run discovery in an approved network, then invoke the exact approved read-only tool before attempting any sensitive operation. |
| AppForge generation pipeline, static preview and ZIP | **Verified** within declared fixtures | Real local HTTP provider pipeline and actual browser preview/export; fixture output is not real vendor generation quality. |
| AppForge vendor-generated quality | **Blocked** | Provider credentials unavailable. |
| AppForge actual dependency build / generated preview | **Blocked** | No Sandbox/OIDC/token/private build key. UI honestly disables managed execution; source editing/export still works. No generated code is executed in the API process. |
| Managed RAG/cloud backup | **Blocked** | No writable managed knowledge database/embedding credentials. Local lexical library is Verified; managed embeddings and live grounded answer quality remain unverified. |
| Android browser layout and offline shell | **Verified** in Chromium emulation | Real device installation, keyboard, TalkBack, OS chrome and safe-area behavior remain Blocked. |
| New hosted hardening commit | **Blocked** | Deployment intentionally withheld; requires approval plus authorized Vercel access. |
| OAuth MCP onboarding, full account/tenant auth, SaaS service provisioning | **Not Implemented** | Existing scope remains private deployment and administrator-configured connectors. |

A hosted MCP reproduction (no credential needed for this attempted read-only server):

```bash
SAARTHI_MCP_SERVERS_JSON='[{"name":"deepwiki","url":"https://mcp.deepwiki.com/mcp","allowed_tools":["read_wiki_structure"]}]' \
  python -c 'from backend.mcp_runtime import list_tools; print(list_tools(force_refresh=True))'
```

Do not weaken destination validation to make this network pass. An approved hosted backend test also needs `SAARTHI_ACCESS_TOKEN`, an admin token, an exact allowlist and successful discovery before invocation. Configure secret values through secure controls; never put them in PR comments or logs.

## Security scope

Focused source/diff review plus regression checks covered shared-service access, owner filters, request-size boundaries, proxy/rate identity, preview CSP/sandbox, secret non-persistence, MCP schemas/approval, path safety and dependency auditing. The formal Codex Security plugin preflight helper was unavailable; no formal scan or absence-of-critical-findings certification is claimed. Public multi-tenant exposure still requires an account/authorization design and distributed edge rate controls. Dependency audits do not prove the absence of source-level vulnerabilities.

## Repeatable checks

```bash
python -m pip install -r requirements.txt
npm ci
python -m pytest -q backend tests
npm run build
npm run test:offline
npx playwright install --with-deps chromium
npm run test:e2e
npm run test:a11y
npm run test:pwa
npm audit --omit=optional
python -m pip_audit -r requirements.txt
```

Each browser runner starts and stops its own backend. The local constrained-environment override was `BROWSER_EXECUTABLE=/tmp/saarthi-chrome`; normal CI uses Playwright's official browser download. CI artifacts include screenshots and JSON evidence. GitHub-hosted results are recorded on PR #20; local passes are not substituted for CI passes.
