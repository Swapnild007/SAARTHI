"""Provider SSE parsing and request-local streaming sink."""
import json
from contextvars import ContextVar

sink = ContextVar('stream_sink', default=None)


def read_completion(response, emit):
    pieces, usage = [], None
    total = 0
    done = False
    for raw in response:
        total += len(raw)
        if total > 1_000_000:
            raise ValueError('Provider stream exceeds response limit')
        line = raw.decode('utf-8').strip()
        if not line.startswith('data:'):
            continue
        data = line[5:].strip()
        if data == '[DONE]':
            done = True
            break
        body = json.loads(data)
        if body.get('error'):
            raise RuntimeError('Provider reported a streaming error')
        usage = body.get('usage') or usage
        choices = body.get('choices') or []
        if choices:
            text = choices[0].get('delta', {}).get('content') or ''
            if isinstance(text, str) and text:
                pieces.append(text)
                emit(text)
            if choices[0].get('finish_reason'):
                done = True
    if not done or not pieces:
        raise RuntimeError('Provider stream ended without a complete answer')
    return ''.join(pieces), usage
