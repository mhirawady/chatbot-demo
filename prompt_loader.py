"""Loads static prompt text once per process."""

from functools import lru_cache
from pathlib import Path

from config import PERSONA_PATH


def _read(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"Prompt asset not found: {path}")
    return path.read_text(encoding="utf-8").strip()


@lru_cache(maxsize=1)
def load_persona() -> str:
    """Return the agent persona text."""
    return _read(PERSONA_PATH)


def build_system_prompt(persona: str, policies: str) -> str:
    """Combine persona and policy text into a single provider-agnostic system prompt."""
    return (
        f"{persona}\n\n"
        "# Policy knowledge base\n\n"
        "The section below is your only authorized source for policy answers. "
        "If a policy question is not answered explicitly here, say you don't "
        "have the answer rather than guessing.\n\n"
        f"{policies}"
    )
