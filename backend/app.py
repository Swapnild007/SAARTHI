from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="SAARTHI Cloud API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("SAARTHI_ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None
    context: dict[str, Any] = {}

@app.get("/api/health")
def health():
    return {"ok": True, "service": "saarthi-api"}

@app.post("/api/chat")
def chat(request: ChatRequest):
    # Provider-agnostic boundary: connect the chosen cloud LLM here.
    # No model key belongs in the browser.
    return {
        "conversation_id": request.conversation_id,
        "reply": "SAARTHI cloud reasoning endpoint is ready.",
        "mode": "cloud",
        "next": "provider_adapter",
    }
