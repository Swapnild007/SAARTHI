"""Request-scoped BYOK configuration. Keys are never stored or returned."""
from contextvars import ContextVar
from typing import Literal
from pydantic import BaseModel, Field, SecretStr

PROVIDERS = {
    'gemini': ('Google Gemini', 'https://generativelanguage.googleapis.com/v1beta/openai'),
    'openrouter': ('OpenRouter', 'https://openrouter.ai/api/v1'),
    'openai': ('OpenAI', 'https://api.openai.com/v1'),
    'groq': ('Groq', 'https://api.groq.com/openai/v1'),
    'mistral': ('Mistral', 'https://api.mistral.ai/v1'),
}
class ProviderSelection(BaseModel):
    provider: Literal['server', 'gemini', 'openrouter', 'openai', 'groq', 'mistral'] = 'server'
    model: str = Field(default='', max_length=160, pattern=r'^[\w./:@-]*$')
    api_key: SecretStr = Field(default=SecretStr(''), max_length=1024)
    allow_fallback: bool = False

selection: ContextVar[ProviderSelection | None] = ContextVar('provider_selection', default=None)

def configured_provider(default):
    from .engine import OpenAICompatibleProvider
    selected = selection.get()
    if selected is None or selected.provider == 'server':
        # Shared provider instances retain last_route/last_failures; never share those across requests.
        import copy
        return copy.copy(default)
    if not selected.api_key.get_secret_value() or not selected.model:
        raise ValueError('Enter a model ID and API key in Settings.')
    provider = OpenAICompatibleProvider()
    label, url = PROVIDERS[selected.provider]
    provider.routes = [{'name': label, 'url': url, 'key': selected.api_key.get_secret_value(), 'model': selected.model}]
    if selected.allow_fallback:
        provider.routes += [dict(route) for route in default.routes if route.get('key')][:1]
    provider.last_failures = []
    return provider
