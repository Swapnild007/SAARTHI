"""Static integration contracts for the SAARTHI/Hermes chat wiring.

These supplement the live gateway and browser tests, not replace them.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_hermes_opt_in_and_existing_chat_fallback():
    js = (ROOT / "scripts" / "app.js").read_text(encoding="utf-8")
    assert "let hermesSelected=false" in js
    assert "SAARTHI default" in js
    assert "if(hermesSelected){" in js
    assert "apiUrl('/api/hermes/chat')" in js
    assert "apiUrl(endpoint,base)" in js
    assert "showResponse(result.reply,result)" in js
    assert "appendConversation('assistant',text,workProduct,complex)" in js


def test_hermes_session_id_reuses_saarthi_thread():
    js = (ROOT / "scripts" / "app.js").read_text(encoding="utf-8")
    assert "conversation_id:thread?.id||null" in js
    assert "saveConversation(currentAssistant)" in js
    assert "loadHistory()" in js


def test_no_static_hermes_credential():
    js = (ROOT / "scripts" / "app.js").read_text(encoding="utf-8")
    assert "let hermesCredential=''" in js
    assert "hermesCredential=entered.trim()" in js
    assert "localStorage.setItem('hermes" not in js.lower()
