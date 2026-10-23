from backend.rag import chunk_text
from backend import mcp_runtime
from backend import rag
import pytest

@pytest.mark.parametrize('query', ['परियोजना जानकारी', 'संशोधन पुरावे निरीक्षणे'])
def test_devanagari_tokens_keep_combining_marks(query):
    assert rag.lexical_terms(query) == query.split()

def test_local_knowledge_retrieval_keeps_multilingual_source_identity(monkeypatch,tmp_path):
    monkeypatch.setenv('SAARTHI_LOCAL_KNOWLEDGE_DB',str(tmp_path/'knowledge.sqlite'))
    monkeypatch.setattr(rag,'_managed_configured',lambda config:False)
    rag.ingest_text('संशोधन करण्यापूर्वी पुरावे आणि निरीक्षणे तपासा.',title='मराठी',source='fixture:marathi')
    rag.ingest_text('Annual leave requires approval.',title='Leave',source='fixture:leave')
    hits=rag.search('संशोधन पुरावे निरीक्षणे')
    assert hits[0]['source']=='fixture:marathi'
    assert hits[0]['similarity']==1

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
