from pathlib import Path

from backend.research import _public_url


ROOT = Path(__file__).resolve().parents[1]


def test_public_url_rejects_private_and_credentialed_urls():
    assert not _public_url("http://localhost:8000")
    assert not _public_url("http://127.0.0.1")
    assert not _public_url("http://user:pass@example.com")
    assert not _public_url("https://example.com:8443")


def test_public_url_allows_standard_public_http_ports(monkeypatch):
    monkeypatch.setattr(
        "backend.research.socket.getaddrinfo",
        lambda host, port: [(2, 1, 6, "", ("93.184.216.34", 0))],
    )
    assert _public_url("https://example.com")
    assert _public_url("http://example.com:80")
    assert _public_url("https://example.com:443")


def test_production_api_hardening_is_configured():
    source = (ROOT / "backend" / "app.py").read_text(encoding="utf-8")
    assert 'allow_origins=ALLOWED_ORIGINS' in source
    assert 'allow_methods=["GET", "POST", "OPTIONS"]' in source
    assert 'X-Content-Type-Options' in source
    assert 'X-Frame-Options' in source
    assert 'Strict-Transport-Security' in source
    assert 'Cache-Control", "no-store"' in source
    assert 'SAARTHI_RATE_LIMIT_PER_MINUTE' in source


def test_mcp_server_url_validation_rejects_local_and_nonstandard_targets(monkeypatch):
    import json
    from backend import mcp_runtime

    monkeypatch.setenv("SAARTHI_MCP_SERVERS_JSON", json.dumps([
        {"name": "local", "url": "https://localhost/mcp", "allowed_tools": ["read"]},
        {"name": "private", "url": "https://127.0.0.1/mcp", "allowed_tools": ["read"]},
        {"name": "query", "url": "https://example.com/mcp?token=inline", "allowed_tools": ["read"]},
        {"name": "port", "url": "https://example.com:8443/mcp", "allowed_tools": ["read"]},
        {"name": "good", "url": "https://mcp.example.com/mcp", "allowed_tools": ["read"]},
    ]))
    servers = mcp_runtime._servers()
    assert [server["name"] for server in servers] == ["good"]


def test_mcp_server_url_validation_rejects_private_ip_ranges(monkeypatch):
    import json
    from backend import mcp_runtime

    monkeypatch.setenv("SAARTHI_MCP_SERVERS_JSON", json.dumps([
        {"name": "loopback", "url": "https://127.0.0.1/mcp", "allowed_tools": ["read"]},
        {"name": "linklocal", "url": "https://169.254.10.20/mcp", "allowed_tools": ["read"]},
        {"name": "public", "url": "https://93.184.216.34/mcp", "allowed_tools": ["read"]},
    ]))
    servers = mcp_runtime._servers()
    assert [server["name"] for server in servers] == ["public"]
