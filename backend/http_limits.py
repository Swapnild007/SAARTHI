"""Bound API bodies before parsing, including chunked requests without Content-Length."""
from starlette.responses import JSONResponse


class RequestBodyLimit:
    def __init__(self, app, maximum=3_000_000):
        self.app = app
        self.maximum = maximum

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or not scope.get('path', '').startswith('/api/'):
            return await self.app(scope, receive, send)
        chunks, size = [], 0
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            chunk = message.get('body', b'')
            size += len(chunk)
            if size > self.maximum:
                response = JSONResponse({'detail': 'Request exceeds 3 MB limit.'}, status_code=413, headers={'Cache-Control': 'no-store'})
                return await response(scope, receive, send)
            chunks.append(chunk)
            if not message.get('more_body', False):
                break
        delivered = False
        async def bounded_receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {'type': 'http.request', 'body': b''.join(chunks), 'more_body': False}
            return await receive()
        await self.app(scope, bounded_receive, send)
