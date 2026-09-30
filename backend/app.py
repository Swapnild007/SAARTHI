from __future__ import annotations

import os
from typing import Any, Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .engine import SaarthiEngine

app = FastAPI(title="SAARTHI Cloud API", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("SAARTHI_ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

Mode = Literal[
    "chat", "help", "research", "search", "analyze", "plan", "remember",
    "recall", "tasks", "task", "remind", "workflow", "workflows",
    "briefing", "system", "settings", "voice",
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


engine = SaarthiEngine()


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "service": "saarthi-api",
        "architecture": "cloud",
        "engine": "jarvis-runtime-v1",
        "provider_configured": engine.cloud.configured,
        "tools": engine.tools.names(),
    }


@app.get("/api/menus")
def menus():
    return {
        "command": ["chat", "voice", "tasks", "actions", "runs"],
        "home": ["briefing", "status", "context"],
        "insights": ["research", "search", "analyze", "web", "sources"],
        "journey": ["tasks", "reminders", "workflows", "progress"],
        "memory": ["remember", "recall", "knowledge", "preferences"],
        "settings": ["model", "voice", "privacy", "connections", "permissions"],
    }


@app.post("/api/command")
def command(request: CommandRequest):
    result = engine.run(
        message=request.message,
        mode=request.mode,
        context=request.context,
    )
    result["conversation_id"] = request.conversation_id
    return result


@app.post("/api/chat")
def chat(request: ChatRequest):
    result = engine.run(
        message=request.message,
        mode="chat",
        context=request.context,
    )
    result["conversation_id"] = request.conversation_id
    return result
