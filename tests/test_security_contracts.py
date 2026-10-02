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
