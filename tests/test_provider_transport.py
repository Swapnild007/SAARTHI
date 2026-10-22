"""Local HTTP provider fixture. Tests adapter transport, not vendor inference."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from fastapi.testclient import TestClient
from backend.app import app, engine
from backend.engine import OpenAICompatibleProvider


def test_real_http_provider_fallback_streaming_and_appforge(monkeypatch):
    requests=[]
    files={'index.html':'<!doctype html><html><head><link rel="stylesheet" href="styles.css"></head><body><button id="count">0</button><script src="app.js"></script></body></html>', 'styles.css':'body { color: teal; }','app.js':'document.getElementById("count").onclick=e=>e.target.textContent=Number(e.target.textContent)+1;'}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def do_POST(self):
            body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            requests.append((self.path,body))
            if self.path.startswith('/rate-limit'):
                self.send_response(429);self.end_headers();return
            if body.get('stream'):
                self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
                for text in ['Transport ','works']:
                    self.wfile.write(('data: '+json.dumps({'choices':[{'delta':{'content':text}}]})+'\n\n').encode());self.wfile.flush()
                self.wfile.write(b'data: [DONE]\n\n');return
            reply=json.dumps({'plan':['Create counter'],'files':files}) if 'complete responsive multi-file' in body['messages'][-1]['content'] else 'Transport works'
            raw=json.dumps({'choices':[{'message':{'content':reply}}]}).encode()
            self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    root=f'http://127.0.0.1:{server.server_port}'
    monkeypatch.setenv('SAARTHI_LLM_ROUTES_JSON',json.dumps([{'name':'limited','url':root+'/rate-limit','key':'fixture-only','model':'test'},{'name':'available','url':root+'/v1','key':'fixture-only','model':'test'}]))
    monkeypatch.setattr(engine,'cloud',OpenAICompatibleProvider())
    try:
        monkeypatch.setenv("SAARTHI_ACCESS_TOKEN", "test-access")
        client=TestClient(app,headers={"X-SAARTHI-Access":"test-access"})
        result=client.post('/api/command',json={'message':'Hello'}).json()
        assert result['reply']=='Transport works'
        assert result['route']=='available'
        assert result['failover']==[{'route':'limited','error':'HTTP 429'}]
        stream=client.post('/api/command/stream',json={'message':'Hello'})
        assert '"type": "delta", "text": "Transport "' in stream.text
        assert 'Transport works' in stream.text
        project=client.post('/api/appforge/generate',json={'prompt':'Create an interactive counter website'}).json()
        assert project['files']==files
        assert project['mode']=='ai-generated'
        assert requests[-1][1]['model']=='test'
        assert all('tools' not in body for _,body in requests)
    finally:
        server.shutdown();server.server_close();thread.join(timeout=2)
