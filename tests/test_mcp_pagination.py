import pytest
from backend import mcp_runtime as mcp

SERVER = {'name':'fixture','allowed_tools':{'first','second'},'allow_write':False}
def tool(name):
    return {'name':name,'inputSchema':{'type':'object'},'annotations':{'readOnlyHint':True}}

def test_discovers_every_catalog_page_and_keeps_session(monkeypatch):
    calls=[]
    monkeypatch.setattr(mcp,'_initialize',lambda server:'session')
    def post(server,payload,session):
        calls.append((payload,session))
        if not payload['params']:
            return {'result':{'tools':[tool('first')],'nextCursor':'page2'}},'updated-session'
        return {'result':{'tools':[tool('second')]}},session
    monkeypatch.setattr(mcp,'_post',post)
    tools=mcp._tools_for_server(SERVER)
    assert [t['_remote_tool'] for t in tools]==['first','second']
    assert calls[1][0]['params']=={'cursor':'page2'}
    assert calls[1][1]=='updated-session'

@pytest.mark.parametrize('catalog',[
    {'tools':[], 'nextCursor':'cycle'},
    {'tools':{}, 'nextCursor':None},
    {'tools':[tool('same'),tool('same')]},
    {'tools':[], 'nextCursor':{}},
])
def test_invalid_or_cyclic_catalog_fails_closed(monkeypatch,catalog):
    monkeypatch.setattr(mcp,'_initialize',lambda server:'session')
    monkeypatch.setattr(mcp,'_post',lambda *args:({'result':catalog},'session'))
    with pytest.raises(RuntimeError):mcp._tools_for_server(SERVER)

def test_invalid_json_schema_is_not_exposed(monkeypatch):
    monkeypatch.setattr(mcp,'_initialize',lambda server:'session')
    broken=tool('broken');broken['inputSchema']={'type':'not-a-json-schema-type'}
    monkeypatch.setattr(mcp,'_post',lambda *args:({'result':{'tools':[broken]}},'session'))
    assert mcp._tools_for_server(SERVER)==[]

def test_revoked_permission_is_enforced_even_when_discovery_is_cached(monkeypatch):
    cached={'function':{'name':'mcp__fixture__first','parameters':{'type':'object'}},'_remote_tool':'first','_server':'fixture','_approved':True,'_safe_to_call':True,'_read_only':True}
    monkeypatch.setattr(mcp,'list_tools',lambda:([cached],[]))
    monkeypatch.setattr(mcp,'_servers',lambda:[{**SERVER,'allowed_tools':set()}])
    monkeypatch.setattr(mcp,'_initialize',lambda *args:pytest.fail('Revoked tool must not execute'))
    with pytest.raises(ValueError,match='no longer configured'):mcp.call_tool('mcp__fixture__first',{})

def test_revoked_write_permission_is_enforced_when_discovery_is_cached(monkeypatch):
    cached={'function':{'name':'mcp__fixture__first','parameters':{'type':'object'}},'_remote_tool':'first','_server':'fixture','_approved':True,'_safe_to_call':True,'_read_only':False}
    monkeypatch.setattr(mcp,'list_tools',lambda:([cached],[]))
    monkeypatch.setattr(mcp,'_servers',lambda:[SERVER])
    monkeypatch.setattr(mcp,'_initialize',lambda *args:pytest.fail('Revoked write must not execute'))
    with pytest.raises(ValueError,match='revoked'):mcp.call_tool('mcp__fixture__first',{},confirmed=True)
