"""Vercel entrypoint for the SAARTHI cloud runtime.

The public GitHub Pages site remains the static frontend. This module exposes
the same FastAPI application as a deployable cloud backend.
"""
from backend.app import app

__all__ = ["app"]
