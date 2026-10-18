from backend.rag import chunk_text
from backend import mcp_runtime

def test_chunk_text_empty_and_bounded():
    assert chunk_text("") == []
    parts = chunk_text(("A sentence with useful context. " * 300), max_chars=500, overlap=60)
    assert len(parts) > 1
    assert all(len(part) <= 500 for part in parts)

def test_mcp_server_requires_https_and_explicit_allowlist(monkeypatch):
    monkeypatch.setenv("SAARTHI_MCP_SERVERS_JSON", '[{"name":"bad","url":"http://localhost:9000/mcp","allowed_tools":["search"]},{"name":"good","url":"https://mcp.example.com","allowed_tools":[]}]')
    servers = mcp_runtime._servers()
    assert len(servers) == 1
    assert servers[0]["name"] == "good"
    assert servers[0]["allowed_tools"] == set()

def test_mcp_status_does_not_expose_secrets(monkeypatch):
    monkeypatch.setenv("SAARTHI_MCP_TOKEN", "never-return-this")
    monkeypatch.setenv("SAARTHI_MCP_SERVERS_JSON", '[{"name":"safe","url":"https://mcp.example.com","token_env":"SAARTHI_MCP_TOKEN","allowed_tools":["search"]}]')
    value = str(mcp_runtime.status())
    assert "never-return-this" not in value
    assert "safe" in value
