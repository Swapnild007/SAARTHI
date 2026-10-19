# SAARTHI local AI runtime

SAARTHI can use an OpenAI-compatible local model server without changing the chat UI or exposing provider routing to the user. This borrows Nanobot's provider-adapter pattern while keeping SAARTHI's existing orchestration, deterministic tools, RAG hooks, MCP allowlist, and response contract.

## Local inference

1. Install and run a local model server such as Ollama, LM Studio, or vLLM on the same host/network as the SAARTHI backend.
2. Pull a model that fits the machine's RAM/VRAM and supports chat completions/tool calling as needed.
3. Set:
   - `SAARTHI_LOCAL_LLM_API_URL=http://127.0.0.1:11434/v1`
   - `SAARTHI_LOCAL_LLM_MODEL=<your-installed-model-id>`
   - `SAARTHI_PREFER_LOCAL=true`
4. Restart the backend and send a normal chat request. No local API key is required for runtimes that do not use one.
5. To prohibit cloud fallback, set `SAARTHI_LOCAL_ONLY=true`. If the local model is unavailable, SAARTHI falls back safely rather than silently switching to a cloud model.

For Ollama, the model identifier must match `ollama list`. Other servers may require a different base URL. `SAARTHI_LOCAL_LLM_API_KEY` is optional for protected local endpoints.

## Ordered route configuration

`SAARTHI_LLM_ROUTES_JSON` accepts an ordered array of route objects. Cloud routes require `key`; routes marked `local: true` may omit it. The local environment variables above add a local route when no local route is already declared. With local preference enabled, local routes are attempted before cloud routes.

## Important network boundary

A local model runs wherever the backend process runs. If SAARTHI is deployed to Vercel or another cloud host, `127.0.0.1` refers to that cloud runtime, not your phone or laptop. A cloud deployment cannot reach a model running on your personal device unless you deliberately provide a secure, reachable network endpoint. Do not expose Ollama or another model port directly to the public internet.

## What is and is not offline

Local inference can make text generation offline-capable. Complete offline operation also requires local knowledge retrieval/embeddings, local persistence, and local implementations for any external tools. Web research, remote MCP servers, hosted embeddings, Supabase persistence, and cloud APIs still require connectivity when configured. SAARTHI should report those capabilities as unavailable rather than pretend they ran.

Nanobot is used as an architectural reference, not embedded as a second user-facing agent runtime. This keeps one SAARTHI experience and avoids running two competing orchestration layers.
