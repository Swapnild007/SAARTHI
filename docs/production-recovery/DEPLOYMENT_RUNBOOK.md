# Private staging and release runbook

1. Keep the candidate on the recovery branch. Create a private staging deployment with Python 3.12 and the root FastAPI entrypoint. Set `SAARTHI_ENV=staging` or `preview`, `SAARTHI_ORIGIN` to that deployment's exact HTTPS origin, and the actual commit via the Vercel SHA or `SAARTHI_COMMIT_SHA`.
2. Provision an isolated Supabase project. Apply `database/recovery.sql` and insert one `saarthi_scope` row with the exact candidate environment. Use the stage project's service role and URL. Apply the migration in a preview database before considering any production database changes. Keep old tables and backups available.
3. Configure a dedicated test owner, a strong generated password and a unique signing key of at least 32 characters via the host's secret manager. Add a staging-only model credential and low provider spend cap. Apply trusted-edge login throttling. Keep Hermes disabled during default-chat validation.
4. Set GitHub environment `saarthi-private-validation` variable `SAARTHI_APPROVED_URL` to the staging origin and secret `SAARTHI_CANDIDATE_PASSWORD` to a staging-only password. Run **Private candidate smoke** from the candidate commit. Verify exact SHA, runtime, completed live inference, recalled test marker and paginated history. The workflow only tests a known private origin and deletes its synthetic thread.
5. Repeat staging tests on desktop and physical Android Chrome. Verify keyboard Send, microphone allowed and denied, zoom and orientation, backup import, network interruption and restart recovery. Inspect browser network activity to confirm requests go to the staging origin. Check that only staging database rows changed. Exercise staging quota and provider limits with synthetic inputs.
6. Preserve any existing Pages and Vercel browser histories from their respective origins before changing traffic. Export with the conversation backup from the original origin once it is available there, and verify import in a fresh browser profile. Delay any origin migration when the original browser records cannot yet be exported.
7. If enabling Hermes, provision a dedicated authenticated HTTPS gateway with tools disabled or explicitly restricted. Test it on a staging deployment first. Set the flag and validated scope only after normal turns, gateway failure, rollout off, and restart tests pass for that gateway. Default chat uses a separate route.
8. Rehearse rollback on staging. Back up the staging database and record the candidate SHA and last compatible staged artifact. Create a synthetic conversation, deploy a second compatible staging revision, then restore the prior staging target. Compare health SHA, run smoke again and reopen the synthetic thread. Rotate test credentials if rollback crosses a secrets change. Avoid rolling back to the audited unauthenticated app with access to the recovery database.
9. Record candidate and rollback evidence in the readiness report. Production promotion and merge require explicit owner approval after review. Preserve the database during application rollback and restore the last approved private artifact.

[Vercel Python runtime configuration](https://vercel.com/changelog/python-3-13-and-3-14-are-now-available)

## Mission 2 staging setup

Use a staging-only Vercel project or a branch-scoped Preview environment. Set `SAARTHI_ENV` and `SAARTHI_ORIGIN` to the actual scope and exact approved HTTPS origin. For Preview, replace the STAGING prefix below with PREVIEW. Install these values in Vercel Environment Variables. Use distinct values from any production integration. A preview ignores unscoped and production credential names.

| Variable | Required value |
| --- | --- |
| `SAARTHI_STAGING_OWNER_ID`, `SAARTHI_STAGING_OWNER_PASSWORD`, `SAARTHI_STAGING_SESSION_KEY` | Dedicated owner, generated password of at least 24 characters and signing key of at least 32 characters |
| `SAARTHI_STAGING_SUPABASE_PROJECT_REF`, `SAARTHI_STAGING_SUPABASE_URL`, `SAARTHI_STAGING_SUPABASE_SERVICE_ROLE_KEY` | Isolated project reference, exact `https://<ref>.supabase.co` and staging service-role secret. Apply `database/recovery.sql` and set `saarthi_scope.environment` in that project. |
| `SAARTHI_STAGING_LLM_ROUTES_JSON` | One or two objects containing `name`, `url`, `key`, and `model`. For hosted admission use `https://openrouter.ai/api/v1` and dedicated capped OpenRouter keys. |
| `SAARTHI_STAGING_LLM_HARD_CAP_CONFIRMED`, `SAARTHI_STAGING_LLM_TURN_RESERVE_MICRO_USD`, `SAARTHI_STAGING_DAILY_BUDGET_MICRO_USD`, `SAARTHI_STAGING_MONTHLY_BUDGET_MICRO_USD` | Set confirmation to `true` after reviewing the cap. Set integer micro-dollar ceilings. Reserve the maximum expected cost across both attempts, including attachments. Each provider key must expose a positive lifetime limit at or below its share of the daily ceiling. Keep key rotations within the same budget period accounted for and never reuse production keys. |

In the isolated Vercel project, add a Firewall custom rate-limit rule matching `POST /api/session/login`, grouped by client IP, with 10 requests per minute and a deny action after the threshold. Verify the configured rule through a controlled rate-limit check on the isolated staging hostname and the Vercel Firewall event log. The durable application-side per-owner gate also applies across instances. Keep provider and database secrets in platform secret settings.

Run the private workflow with the approved staging URL and `turns=16` for 32 transcript messages and a fresh-session reopen. Observe exact SHA, actual provider replies, ordered pagination, same-turn replay and cleanup. For a controlled upstream failure, use a separate staging build with an intentionally unavailable staging route and verify the typed failure and successful recovery after restoring the capped staging route. Preserve synthetic data across the backend restart and verify terminal-turn replay.

For rollback, set `SAARTHI_APPROVED_ROLLBACK_URL`, `SAARTHI_ROLLBACK_SHA` and the `SAARTHI_ROLLBACK_PASSWORD` secret in the private GitHub environment. Use a distinct compatible staging build sharing the isolated database. Run the workflow with `verify_rollback=true` before changing traffic. Record the staging traffic switch separately, then verify the alias's returned health SHA and reopen a separate synthetic thread created before the switch. The workflow tests compatibility and never switches traffic itself.

For optional Hermes use the scope-prefixed `HERMES_ENABLED`, `HERMES_VALIDATED_SCOPE`, `HERMES_URL`, `HERMES_API_KEY`, `HERMES_TOOLS_DISABLED_CONFIRMED`, `HERMES_HARD_CAP_CONFIRMED` and `HERMES_TURN_RESERVE_MICRO_USD`. The gateway operator must verify server-side tool restrictions and hard spend control. Run authenticated restore, timeout, outage and restart checks before rollout.

### Physical Android Chrome acceptance

1. Open the approved staging URL and sign in with its dedicated owner account. Tap the composer and test the keyboard Send action and the on-screen Send button.
2. Send a long-response request. Scroll through the reply and back to the composer. Rotate portrait to landscape and back with both keyboard states.
3. Select, send and remove a safe CSV. Allow microphone access and send one voice turn, then deny it and confirm the message and typed recovery.
4. Reopen history after reload. Confirm the current and prior threads are present. Run a controlled timeout and verify subsequent Send works.
5. Record Chrome and Android versions, app SHA, results, and screenshots with synthetic content and no secrets.

[Vercel WAF rate limiting](https://vercel.com/docs/vercel-firewall/vercel-waf/rate-limiting) · [OpenRouter key limits](https://github.com/OpenRouterTeam/docs/blob/main/api_reference/limits.mdx)

If GitHub does not register the branch-only workflow for manual dispatch, run `python scripts/candidate_smoke.py` from the exact branch SHA in a trusted runner with the same workflow environment variables injected by its secret manager.

## Mobile owner setup and recovery

The primary setup is inside SAARTHI. The previous terminal helper is a legacy maintenance tool and is unnecessary for mobile onboarding.

1. Open the approved Preview URL in Android Chrome, select **Private sign-in**, then **Set up / recover account**.
2. If the wizard says the conversation database is disconnected, connect the Supabase plugin in ChatGPT and authorize an isolated SAARTHI project. Activation can apply the repository migration through that authorized connection. The app cannot provision or migrate an account that is not connected.
3. When connections are ready, use the wizard's **Open Vercel tokens** link. Sign in to the Vercel account that can manage SAARTHI. Create a temporary access token for the project team with the shortest available expiry. Return to SAARTHI and paste it in the password-style field, then select **Verify ownership**.
4. The server checks management write permission through a temporary Preview-branch environment record and removes it. It stores a ten-minute, one-use setup authorization in the existing private database. The Vercel token is not persisted. Revoke it in Vercel after verification.
5. Create and repeat your own password in the app. It is hashed on the server and saved atomically with consumption of the setup authorization. You are signed in immediately. No restart or password-hash copy is required.
6. For a forgotten password, reopen the same wizard and choose **Recover or change password**. Repeat management verification. Saving a replacement password invalidates earlier sessions in builds using database authentication and preserves the owner identity and conversations.
7. Use **Sign out** in the sign-in dialog to remove the browser session. Valid sessions survive reload for up to one hour. Reauthenticate after expiry and restore the cloud conversation history.

First-time setup closes when the credential exists. A new first-time grant is refused. Recovery always requires fresh deployment-management verification. Expired or consumed grants cannot set a password.

### Automated deployment preparation

The recovery branch's Preview environment was prepared through the connected Vercel API with a generated session key, stable owner ID, database authentication mode, and pinned project and team identifiers. Preview origin derives from Vercel's current deployment URL when no explicit origin is set. No owner needs to edit those values. The configured keys are recorded here for maintainers, outside the product flow.

- `SAARTHI_ENV=preview`
- `SAARTHI_PREVIEW_OWNER_AUTH_STORE=database`
- `SAARTHI_PREVIEW_OWNER_ID`
- `SAARTHI_PREVIEW_SESSION_KEY`
- `SAARTHI_PREVIEW_DEPLOYMENT_PROJECT_ID`
- `SAARTHI_PREVIEW_DEPLOYMENT_TEAM_ID`

The existing Supabase project must receive `database/recovery.sql`, including owner credentials and one-time grants. That script adds tables and functions without deleting saved conversations. Store credentials remain exclusively server-side. The authenticated Supabase connector can perform this migration after the owner connects the account and authorizes the isolated project.

Model credentials, a verified spending ceiling, and the isolated database are still required for actual AI chat. Use authorized connectors or the hosting secret manager to configure those resources. Neither the wizard nor a passing fixture test certifies live inference.

Old deployments retain their own build configuration. Protect or retire old previews during recovery rollout. Scope-prefixed Vercel settings, the private database marker, and provider admission limits remain enforced.
