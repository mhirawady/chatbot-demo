"""Static configuration for the airline customer service chatbot demo."""

import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(PROJECT_ROOT / ".env")

ProviderName = Literal["anthropic", "openrouter"]

ACTIVE_PROVIDER: ProviderName = "openrouter"


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"{name} is not set. Copy .env.example to .env and fill it in."
        )
    return value


# Real keys live in .env (gitignored), never in this file.
ANTHROPIC_API_KEY = _require_env("ANTHROPIC_API_KEY")
OPENROUTER_API_KEY = _require_env("OPENROUTER_API_KEY")

ANTHROPIC_MODEL = "claude-sonnet-5"
OPENROUTER_MODEL = "anthropic/claude-sonnet-5"

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

MAX_TOKENS = 2048
REQUEST_TIMEOUT_SECONDS = 120

# Provider round-trips allowed per user turn before the turn is abandoned.
MAX_TOOL_ROUNDTRIPS = 10

PERSONA_PATH = PROJECT_ROOT / "config" / "persona.md"
POLICIES_PATH = PROJECT_ROOT / "knowledge_base" / "policies.md"
BOOKINGS_PATH = PROJECT_ROOT / "mock_data" / "bookings.json"
FLIGHTS_PATH = PROJECT_ROOT / "mock_data" / "flights.json"

EXIT_COMMANDS = frozenset({"exit", "quit"})

# Deterministic backstop for the LLM-driven end_conversation tool.
RESET_PHRASES = (
    "new chat",
    "new conversation",
    "start over",
    "start again",
    "different topic",
    "something else",
    "change the subject",
    "reset",
)

WELCOME_MESSAGE = (
    "Hi, I'm Sunny with SkyHop Airlines. I can help with bookings, flight "
    "status, changes, and cancellations — what can I do for you today?"
)

CLOSING_LINE = (
    "Of course — I'll close this out here. Whenever you're ready, "
    "just tell me what you'd like help with next."
)

TOOL_LIMIT_MESSAGE = (
    "I'm sorry, I wasn't able to pull that together just now. "
    "Could you try asking again?"
)
