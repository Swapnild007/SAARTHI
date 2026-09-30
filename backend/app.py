from __future__ import annotations

import os
from typing import Any, Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="SAARTHI Cloud API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("SAARTHI_ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

Mode = Literal[
    "chat", "help", "research", "search", "analyze", "remember",
    "recall", "tasks", "remind", "workflows", "briefing", "system",
    "settings", "voice",
]

class CommandRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12000)
    mode: Mode = "chat"
    conversation_id: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12000)
    conversation_id: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)

def route(mode: Mode) -> dict[str, Any]:
    capabilities = {
        "chat": ["llm"],
        "help": ["command_catalog"],
        "research": ["web_search", "source_collection", "llm"],
        "search": ["web_search"],
        "analyze": ["llm", "context"],
        "remember": ["memory_write"],
        "recall": ["memory_search", "llm"],
        "tasks": ["task_manager"],
        "remind": ["scheduler"],
        "workflows": ["workflow_engine"],
        "briefing": ["calendar", "tasks", "weather", "news"],
        "system": ["health", "telemetry"],
        "settings": ["preferences", "connections"],
        "voice": ["speech_to_text", "llm", "text_to_speech"],
    }
    return {"mode": mode, "capabilities": capabilities[mode]}

@app.get("/api/health")
def health():
    return {"ok": True, "service": "saarthi-api", "architecture": "cloud"}

@app.get("/api/menus")
def menus():
    return {
        "command": ["chat", "voice", "tasks", "actions"],
        "home": ["briefing", "status", "context"],
        "insights": ["research", "search", "analyze", "web"],
        "journey": ["tasks", "reminders", "workflows", "progress"],
        "memory": ["remember", "recall", "knowledge"],
        "settings": ["model", "voice", "privacy", "connections"],
    }

@app.post("/api/command")
def command(request: CommandRequest):
    target = route(request.mode)
    return {
        "ok": True,
        "mode": request.mode,
        "capabilities": target["capabilities"],
        "reply": f"Command routed to {request.mode}.",
        "execution": "adapter_pending",
    }

@app.post("/api/chat")
def chat(request: ChatRequest):
    return {
        "conversation_id": request.conversation_id,
        "reply": "SAARTHI cloud reasoning endpoint is ready.",
        "mode": "cloud",
        "next": "provider_adapter",
    }
