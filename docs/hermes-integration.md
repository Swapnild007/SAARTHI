# Hermes Agent bridge (opt-in)

SAARTHI remains the primary application. This integration adds an isolated, authenticated server-to-server route. It does not change the current SAARTHI chat, frontend, provider selection, history, or memory implementation.

## Configuration

Run a separately installed NousResearch/hermes-agent gateway and enable its OpenAI-compatible API. Configure the following **server-side** environment variables in SAARTHI:

- `SAARTHI_HERMES_ENABLED=true`
- `SAARTHI_HERMES_URL=http://127.0.0.1:8642` (local gateway; remote requires HTTPS)
- `SAARTHI_HERMES_API_KEY=<Hermes API_SERVER_KEY>`
- `SAARTHI_HERMES_BRIDGE_KEY=<separate strong caller secret>`

The Hermes gateway must be reachable **from the SAARTHI backend**, not from the user's browser. Vercel cannot reach a gateway bound to localhost on another machine. Use an authenticated private HTTPS gateway or run both processes on a trusted host. Never publish the gateway with terminal/file tools enabled without strict isolation and access controls.

## Endpoints

- `GET /api/hermes/status`: returns whether bridge is configured; no secrets.
- `POST /api/hermes/chat`: requires `Authorization: Bearer <SAARTHI_HERMES_BRIDGE_KEY>`, body `{"message":"Hello","conversation_id":"optional-session-key"}`.

Conversation IDs are forwarded as Hermes session keys. The adapter intentionally does not pass arbitrary tools, system prompts, or API parameters from callers.

## Scope and limitations

This is a backend integration foundation, not a public browser chat switch. No browser-accessible secret is provided, no production gateway is provisioned, and existing SAARTHI routes remain untouched. A user-authenticated backend session and UI provider selector must be designed before enabling Hermes for public SAARTHI users. The existing 28-second SAARTHI command deadline is not applied to this isolated endpoint; it has its own 25-second cap.

Run `pytest tests/test_hermes_bridge.py` after installing the project's requirements. Do not mark live inference as verified until the configured Hermes gateway is exercised end-to-end.
