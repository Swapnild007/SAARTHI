import json
from pathlib import Path
from fastapi.testclient import TestClient
import pytest
from backend.app import app, engine
from backend.storage import CloudStore
from backend.appforge_sandbox import validate_build_files, BuildInputError


def test_shared_services_fail_closed_without_private_access(monkeypatch):
    class PrivateStore:
        configured = True
    monkeypatch.delenv('SAARTHI_ACCESS_TOKEN', raising=False)
    monkeypatch.setattr(app.state, 'cloud_store', PrivateStore())
    client = TestClient(app)
    assert client.get('/api/health').status_code == 200
    response = client.get('/api/conversations', params={'session_id':'sample'})
    assert response.status_code == 503
    assert response.headers['cache-control'] == 'no-store'


def test_token_rejection_has_cors_headers(monkeypatch):
    monkeypatch.setenv('SAARTHI_ACCESS_TOKEN','private-access')
    response = TestClient(app).get('/api/providers',headers={'Origin':'https://swapnild007.github.io'})
    assert response.status_code == 401
    assert response.headers['access-control-allow-origin'] == 'https://swapnild007.github.io'


def test_chunked_oversized_input_is_rejected_before_parsing():
    def chunks():
        yield b'x'*1_600_000
        yield b'x'*1_600_000
    response = TestClient(app).post('/api/command/plain',content=chunks(),headers={'Content-Type':'text/plain'})
    assert response.status_code == 413


def test_conversation_write_checks_owner_before_message_append(monkeypatch):
    store=CloudStore();calls=[]
    monkeypatch.setattr(store,'ensure_user',lambda uid:None)
    def request(path,**kwargs):
        calls.append((path,kwargs))
        return [{'id':'11111111-1111-4111-8111-111111111111','user_id':'another-owner'}]
    monkeypatch.setattr(store,'_request',request)
    with pytest.raises(ValueError,match='does not belong'):
        store.save_turn(session_id='session',conversation_id='11111111-1111-4111-8111-111111111111',user_content='hello',assistant_content='world')
    assert all(path != 'messages' for path,_ in calls)


def test_conversation_query_rejects_filter_injection(monkeypatch):
    store=CloudStore()
    monkeypatch.setattr(store,'_request',lambda *args,**kwargs:pytest.fail('No request for malformed identity'))
    assert store.messages('session','x&user_id=neq.other') == []


def test_package_build_cannot_succeed_without_build_script():
    with pytest.raises(BuildInputError,match='build script'):
        validate_build_files({'package.json':'{"name":"no-build"}','index.html':'<html></html>'})


def test_release_branch_never_autodeploys():
    config=json.loads(Path('vercel.json').read_text())
    assert config['git']['deploymentEnabled']['feat/saarthi-1-release'] is False


@pytest.mark.parametrize("scripts", [None, [], "npm run build", 42])
def test_package_build_rejects_invalid_script_container(scripts):
    with pytest.raises(BuildInputError,match='scripts must be an object'):
        validate_build_files({'package.json':json.dumps({'scripts':scripts})})
