import base64
import io
import json
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
import pytest
from backend.app import app, engine
from backend.calculator import calculate
from backend.provider_settings import ProviderSelection, configured_provider, selection
from backend.streaming import read_completion

@pytest.mark.parametrize('expression,expected', [('(12 + 8) * 3',60),('15% of 200',30),('calculate 100 / (5 + 5)',10),('-2 * -3',6)])
def test_arithmetic_preserves_grouping(expression,expected):
    assert calculate(expression)['value']==expected

@pytest.mark.parametrize('expression',['2 ** 99999999','1 / 0','__import__("os")','9 ** 9 ** 9','2 + time'])
def test_arithmetic_rejects_unsafe_or_undefined_input(expression):
    with pytest.raises((ValueError,SyntaxError)):
        calculate(expression)

def test_calculator_never_substitutes_time():
    client=TestClient(app)
    for message in ['calculator','Calculate (12 + 8) * 3','calculate 15% of 200']:
        result=client.post('/api/command',json={'message':message}).json()
        assert result['intent']['name']=='calculate'
        assert result['provider']=='system.calculate'
        assert 'system.time' not in result['tool_results']

def test_provider_credentials_are_request_local():
    def request(key):
        token=selection.set(ProviderSelection(provider='groq',model='test-model',api_key=key))
        try:
            provider=configured_provider(engine.cloud)
            assert provider.routes[0]['key']==key
            return provider.routes[0]['url']
        finally:
            selection.reset(token)
    with ThreadPoolExecutor(2) as pool:
        assert len(list(pool.map(request,['key-one','key-two'])))==2
    assert selection.get() is None

def test_validation_never_echoes_secret_input():
    result=TestClient(app).post('/api/command',json={'message':'hello','provider_settings':{'provider':'bad','api_key':'private-secret'}})
    assert result.status_code==422
    assert 'private-secret' not in result.text

def test_provider_selection_reaches_actual_adapter_without_mutation(monkeypatch):
    captured=[]
    def generate(self,**kwargs):
        captured.append(self.routes[0].copy())
        return 'configured answer',None
    monkeypatch.setattr('backend.engine.OpenAICompatibleProvider.generate',generate)
    original=[dict(r) for r in engine.cloud.routes]
    response=TestClient(app).post('/api/command',json={'message':'Hello','provider_settings':{'provider':'gemini','model':'chosen-model','api_key':'session-secret'}})
    assert response.json()['reply']=='configured answer'
    assert captured[0]['url']=='https://generativelanguage.googleapis.com/v1beta/openai'
    assert captured[0]['model']=='chosen-model'
    assert 'session-secret' not in response.text
    assert engine.cloud.routes==original

def test_streaming_parser_receives_real_sse_events():
    chunks=[]
    response=iter([b'data: {"choices":[{"delta":{"content":"Hello "}}]}\n',b'\n',b'data: {"choices":[{"delta":{"content":"world"},"finish_reason":"stop"}]}\n',b'data: [DONE]\n'])
    assert read_completion(response,chunks.append)[0]=='Hello world'
    assert chunks==['Hello ','world']

def test_streaming_parser_rejects_truncated_output():
    with pytest.raises(RuntimeError):
        read_completion(iter([b'data: {"choices":[{"delta":{"content":"partial"}}]}\n']),lambda x:None)

def test_streaming_http_preserves_result_and_context_isolation(monkeypatch):
    from backend.streaming import sink
    def run(**kwargs):
        assert selection.get().model=='stream-model'
        sink.get()('hello ')
        sink.get()('stream')
        return {'ok':True,'reply':'hello stream','provider':'test'}
    monkeypatch.setattr(engine,'run',run)
    response=TestClient(app).post('/api/command/stream',json={'message':'Hello','provider_settings':{'provider':'groq','model':'stream-model','api_key':'never-output'}})
    events=[json.loads(line[6:]) for line in response.text.splitlines() if line.startswith('data: ')]
    assert ''.join(e.get('text','') for e in events)=='hello stream'
    assert events[-1]['result']['reply']=='hello stream'
    assert 'never-output' not in response.text

def test_pdf_extraction_contract_for_plain_document():
    response=TestClient(app).post('/api/knowledge/extract',json={'name':'policy.txt','type':'text/plain','data':base64.b64encode(b'Escalate at ninety percent.').decode()})
    assert response.status_code==200
    assert 'ninety percent' in response.json()['text']

def test_appforge_multi_file_generation_validation_and_export(monkeypatch):
    files={'index.html':'<!doctype html><html><head><link rel="stylesheet" href="styles.css"></head><body><button>Count</button><script src="app.js"></script></body></html>','styles.css':'body { color: teal }','app.js':'document.querySelector("button").textContent="Ready";'}
    monkeypatch.setattr(engine,'run',lambda **kwargs:{'reply':json.dumps({'plan':['Create interactive counter'],'files':files})})
    client=TestClient(app)
    generated=client.post('/api/appforge/generate',json={'prompt':'Create a responsive counter application'}).json()
    assert generated['mode']=='ai-generated'
    assert generated['files']==files
    assert 'execution not performed' in generated['validation']
    from zipfile import ZipFile
    exported=client.post('/api/appforge/export',json={'files':generated['files']})
    with ZipFile(io.BytesIO(exported.content)) as archive:
        assert set(archive.namelist())==set(files)

def test_deployment_access_control(monkeypatch):
    monkeypatch.setenv('SAARTHI_ACCESS_TOKEN','deployment-secret')
    client=TestClient(app)
    assert client.get('/api/health').status_code==200
    assert client.get('/api/providers').status_code==401
    assert client.get('/api/providers',headers={'X-SAARTHI-Access':'deployment-secret'}).status_code==200

def test_pwa_manifest_and_service_worker_are_served():
    client=TestClient(app)
    manifest=client.get('/manifest.webmanifest').json()
    assert manifest['display']=='standalone'
    for icon in manifest['icons']:
        assert client.get(icon['src']).content.startswith(b'\x89PNG')
    sw=client.get('/sw.js')
    assert sw.status_code==200 and sw.headers['cache-control']=='no-cache'
