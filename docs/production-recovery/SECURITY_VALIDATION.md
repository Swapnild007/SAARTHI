# Security validation

- Protected commands, cloud history and usage require a valid deployment-scoped owner session. The API ignores browser ownership claims. Sessions expire after one hour. Rotating the session key or owner password revokes previously issued tokens. Logout removes the browser cookie.
- Cookie attributes include HttpOnly, SameSite Strict and Secure on HTTPS. State-changing requests reject mismatched Origin values. The configured origin must match the request. Protected routes reject absent configuration before chat can reach the provider.
- The database marker is checked before conversation operations. Turn and history predicates use the server-derived owner. Cross-owner denial is verified at the API fixture and database SQL levels. Database service and Hermes credentials stay server-side.
- Requests are size-bounded and validated with redacted errors. Attachments have batch and count limits, terminal model failures use generalized messages, and hosted workers reject provider redirects. Runtime logging records turn IDs, states and timing, without the submitted prompt or credentials.
- Login and API rate limits are per process. The database daily quota survives restarts and reserves a slot ahead of provider work. Configure a trusted-edge login throttle and hard provider account budget before a private release. Per-call output is bounded for the default model path.
- The database keeps recovery conversations until authenticated deletion. Deletion cascades to turns. Local backups are explicit files with message text and remain under the owner's control. Browser-local removal and cloud deletion have separate effects. Any provider-side retention needs to be confirmed on the selected account.
- Remote retrieval, tool execution and standalone saved facts are unavailable in this candidate. Hermes requires an isolated tool-restricted gateway and independent validation before the scoped feature flag is set.
- Live access control at the deployed edge, hosted Supabase isolation, external provider retention, and independent production security sign-off remain open.

## Mission 2 controls

Hosted resource and owner credentials are scope-prefixed. The database endpoint must match the explicitly configured Supabase project reference, and its scope marker is checked before conversation reads and writes. Login also uses a durable, per-owner database limit. Hosted default provider calls first check the selected OpenRouter key's lifetime ceiling and remaining credit. Provider credentials and raw cap responses stay on the server.

The admission transaction serializes per-owner usage, reserves the full configured turn cost against UTC daily and monthly ceilings, and keeps the reservation across replay, deletion and failure. Reported provider cost is recorded when present. Unknown charges, unsuccessful attempts and reporting failures never release the conservative reservation. Live billing closeout, trusted-edge deployment, secret separation, and retention verification remain staging work.

## Browser ownership verification

Setup authorization requires deployment management write access. The API uses a temporary Vercel token only against Vercel's fixed HTTPS API, creates a harmless branch-scoped permission-check record and removes it before issuing authorization. Setup tokens are random, ten-minute, HttpOnly cookies. Only their environment- and origin-bound hashes are stored. The database enforces expiration and one-use consumption under an owner lock. First-time issuance refuses an existing owner credential. Recovery requires new management verification, rotates the password hash used to sign sessions and retains owner identity.

Owner and setup tables have RLS enabled and grant access only to the server service role. Invalid password requests, cross-origin requests, missing database configuration, expired authorizations and replays are denied. KDF work runs outside the event loop. The UI clears token and password fields after use and does not save them in browser storage. A deployment management token can be revoked in Vercel after verification. Live verification still requires the owner to connect the private database.
