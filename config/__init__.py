"""Static configuration for the airline customer service chatbot demo."""

from pathlib import Path
from typing import Literal

PROJECT_ROOT = Path(__file__).resolve().parent.parent

ProviderName = Literal["anthropic", "openrouter"]

ACTIVE_PROVIDER: ProviderName = "anthropic"

# DEMO ONLY: deliberate exception to the repo rule against hardcoded credentials.
# Replace locally and never commit a real key.
ANTHROPIC_API_KEY = "REPLACE_ME"
OPENROUTER_API_KEY = "REPLACE_ME"

ANTHROPIC_MODEL = "claude-sonnet-5"
OPENROUTER_MODEL = "anthropic/claude-sonnet-5"

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

MAX_TOKENS = 2048
REQUEST_TIMEOUT_SECONDS = 60

# Provider round-trips allowed per user turn before the turn is abandoned.
MAX_TOOL_ROUNDTRIPS = 3

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

CLOSING_LINE = (
    "Of course — I'll close this out here. Whenever you're ready, "
    "just tell me what you'd like help with next."
)

TOOL_LIMIT_MESSAGE = (
    "I'm sorry, I wasn't able to pull that together just now. "
    "Could you try asking again?"
)
