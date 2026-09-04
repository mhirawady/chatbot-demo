"""HTTP API and static UI for the SkyHop Airlines customer service agent."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from config import ACTIVE_PROVIDER, WELCOME_MESSAGE
from orchestration import Orchestrator, TurnOutcome
from providers import build_provider, resolve_model

WEB_DIR = Path(__file__).resolve().parent / "web"

app = FastAPI(title="SkyHop Chatbot Demo")
_sessions: dict[str, Orchestrator] = {}


def create_orchestrator() -> Orchestrator:
    """Build a fresh orchestrator for one browser session."""
    provider_name = ACTIVE_PROVIDER
    return Orchestrator(build_provider(provider_name), resolve_model(provider_name))


class SessionResponse(BaseModel):
    session_id: str
    welcome: str


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1)
    message: str = Field(min_length=1)


class ChatResponse(BaseModel):
    reply: str | None
    outcome: Literal["continue", "reset", "exit"]


@app.post("/api/session", response_model=SessionResponse)
def start_session() -> SessionResponse:
    """Create a new conversation and return its id plus the welcome line."""
    session_id = str(uuid.uuid4())
    _sessions[session_id] = create_orchestrator()
    return SessionResponse(session_id=session_id, welcome=WELCOME_MESSAGE)


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """Run one passenger turn against the session's orchestrator."""
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="message must not be blank")

    orchestrator = _sessions.get(request.session_id)
    if orchestrator is None:
        raise HTTPException(status_code=404, detail="Unknown session_id")

    result = orchestrator.handle_input(message)
    if result.outcome is TurnOutcome.EXIT:
        # Browser UI does not quit the process; recycle the session instead.
        orchestrator.reset()
    return ChatResponse(reply=result.reply, outcome=result.outcome.value)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
