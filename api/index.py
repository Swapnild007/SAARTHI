"""Vercel ASGI entrypoint for the SAARTHI cloud runtime.

Vercel discovers Python serverless functions from the api/ directory.  Keep
the application itself in backend/ so local development and tests continue to
use the same FastAPI instance.
"""

from backend.app import app

__all__ = ["app"]
