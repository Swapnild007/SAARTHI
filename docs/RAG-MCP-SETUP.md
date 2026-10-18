# SAARTHI managed RAG and remote MCP setup

SAARTHI remains a serverless application. GitHub Pages serves the static frontend and Vercel runs the FastAPI API. This design does not require a dedicated VM, Docker host, or self-managed MCP server.

## 1. Managed RAG

### Required managed services
- A Supabase project with Postgres and the pgvector extension.
- An OpenAI-compatible embeddings endpoint and a model that returns 1536-dimensional vectors. The example configuration uses \`text-embedding-3-small\`.

### Setup
1. Open the Supabase SQL editor for the project already used by SAARTHI, if available.
2. Run \`database/rag_schema.sql\` once.
3. In Vercel Project Settings → Environment Variables, set:
   - \`SAARTHI_SUPABASE_URL\`: the project URL.
   - \`SAARTHI_SUPABASE_SERVICE_ROLE_KEY\`: service-role key, server-side only.
   - \`SAARTHI_EMBEDDING_API_URL\`: embeddings API base URL, such as \`https://api.openai.com/v1\`.
   - \`SAARTHI_EMBEDDING_API_KEY\` and \`SAARTHI_EMBEDDING_MODEL\`.
   - \`SAARTHI_KNOWLEDGE_ADMIN_TOKEN\`: a long random secret used to protect ingestion and admin search.
4. Redeploy the Vercel project so the serverless functions receive the new variables.
5. Check \`/api/rag/status\` and \`/api/health\`. Status only confirms configuration presence, not database connectivity.
6. Ingest text or a supported base64 attachment through \`POST /api/knowledge/ingest\` with \`Authorization: Bearer <SAARTHI_KNOWLEDGE_ADMIN_TOKEN>\`. Supported parsers include text, Markdown, CSV, JSON, PDF text extraction, and Excel workbooks. Image OCR and full 1000-page document ingestion are not included in this first implementation.
7. SAARTHI attempts semantic retrieval before model generation. If RAG is not configured or retrieval fails, normal chat continues without retrieved evidence.

Example text ingestion body:

\`\`\`json
{
  "title": "System design notes",
  "source": "internal://system-design-notes",
  "collection": "default",
  "text": "Paste the source text here."
}
\`\`\`

The current schema uses 1536-dimensional embeddings. Do not switch to an embedding model with a different vector dimension without updating the schema and dimension validation together.

## 2. Remote MCP tools

SAARTHI is the MCP client. Remote MCP servers are operated by third parties or managed providers. No MCP server is deployed by SAARTHI.

### Configure a remote server
Add a JSON array to the Vercel environment variable \`SAARTHI_MCP_SERVERS_JSON\`. Every endpoint must use HTTPS. Keep tokens in separate server-side environment variables.

Example shape (replace the placeholder with a provider's documented remote endpoint):

\`\`\`json
[
  {
    "name": "provider_tools",
    "url": "https://your-managed-provider.example/mcp",
    "token_env": "SAARTHI_PROVIDER_MCP_TOKEN",
    "enabled": true,
    "allowed_tools": ["search_documents", "get_document"],
    "allow_write": false
  }
]
\`\`\`

- \`allowed_tools\` is an explicit allowlist of remote tool names.
- Read-only tools are the only tools exposed to the model by default.
- Non-read-only tools are blocked unless \`allow_write\` is explicitly set to \`true\`. Grant write access only to narrowly reviewed tools.
- The provider endpoint, token format, and available tool names must come from that provider's documentation/account. SAARTHI does not guess endpoints or credentials.
- The client uses MCP Streamable HTTP, bounded timeouts, a small tool-call limit, and no more than one model-to-tool round-trip per response.

### Discover tools and verify configuration
1. Set \`SAARTHI_KNOWLEDGE_ADMIN_TOKEN\` as above.
2. Configure the remote endpoint with \`allowed_tools: []\` initially.
3. Call \`GET /api/mcp/tools\` with the admin bearer token. The response lists remote tool names and marks each as approved or blocked; it does not execute them.
4. Add only the required exact tool names to \`allowed_tools\`. Keep \`allow_write\` false unless a reviewed workflow requires write operations.
5. Redeploy and call \`GET /api/mcp/status\`. Use \`/api/health\` for the overall configuration summary.

## 3. Important operational boundaries

- Environment variables are server-side only. Never put Supabase service-role keys, MCP tokens, or the admin token in HTML, JavaScript, public repository files, or browser local storage.
- RAG ingestion and admin search require the admin bearer token. The normal assistant retrieves knowledge internally.
- Remote MCP output and retrieved documents are treated as untrusted content.
- Remote MCPs and embeddings can incur provider usage charges and depend on provider availability. No server cost is introduced, but third-party usage may not be free.
- The application code is committed, but RAG remains inactive until managed database, embedding credentials, schema setup, and deployment variables are configured. MCP tool execution remains inactive until at least one remote endpoint and explicit tool allowlist are configured.
