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


def test_served_composer_has_security_headers():
    from fastapi.testclient import TestClient
    from backend.app import app

    client = TestClient(app, base_url="https://testserver")
    for path in ("/", "/command-center.html"):
        response = client.get(path)
        assert response.status_code == 200
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert "max-age=31536000" in response.headers["Strict-Transport-Security"]
        policy = response.headers["Content-Security-Policy"]
        assert "script-src 'self';" in policy and ".vercel.app" not in policy
        assert "<script>" not in response.text
