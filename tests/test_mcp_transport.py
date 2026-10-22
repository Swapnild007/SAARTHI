"""Real local HTTP protocol fixture. Does not certify any externally hosted connector."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
import pytest
from backend import mcp_runtime as mcp


def test_mcp_http_initialize_202_discovery_schema_and_invocation(monkeypatch):
    received=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def do_POST(self):
            body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            received.append(body)
            if body['method']=='notifications/initialized':
                self.send_response(202);self.end_headers();return
            result={
                'initialize':{'protocolVersion':'2025-03-26','capabilities':{'tools':{}},'serverInfo':{'name':'fixture','version':'1'}},
                'tools/list':{'tools':[{'name':'lookup','description':'Read a record','inputSchema':{'type':'object','properties':{'id':{'type':'integer'}},'required':['id'],'additionalProperties':False},'annotations':{'readOnlyHint':True}}, {'name':'delete','inputSchema':{'type':'object'},'annotations':{'readOnlyHint':False}}]},
                'tools/call':{'content':[{'type':'text','text':'record found'}]},
            }[body['method']]
            raw=json.dumps({'jsonrpc':'2.0','id':body['id'],'result':result}).encode()
            self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Mcp-Session-Id','fixture-session');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    fixture={'name':'fixture','url':f'http://127.0.0.1:{server.server_port}/mcp','token':'','allowed_tools':{'lookup','delete'},'allow_write':True}
    # Only this test fixture can use loopback; production validation remains enabled.
    monkeypatch.setattr(mcp,'_servers',lambda:[fixture])
    monkeypatch.setattr('backend.research._public_url',lambda url:url==fixture['url'])
    monkeypatch.setattr(mcp,'_cache',{'at':0,'tools':[],'errors':[]})
    try:
        tools,errors=mcp.list_tools(force_refresh=True)
        assert not errors and len(tools)==2
        read=tools[0]['function']['name'];write=tools[1]['function']['name']
        assert 'record found' in mcp.call_tool(read,{'id':7})['result']
        count=len(received)
        with pytest.raises(ValueError,match='schema'):mcp.call_tool(read,{'id':'bad'})
        assert len(received)==count
        with pytest.raises(ValueError,match='confirmation'):mcp.call_tool(write,{})
        assert [t['function']['name'] for t in mcp.openai_tool_definitions()]==[read]
        assert 'record found' in mcp.call_tool(write,{},confirmed=True)['result']
    finally:
        server.shutdown();server.server_close();thread.join(timeout=2)
