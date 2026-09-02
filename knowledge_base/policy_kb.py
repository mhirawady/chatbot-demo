"""Interface over the airline policy knowledge base."""

from functools import lru_cache
from pathlib import Path

from config import POLICIES_PATH


class PolicyKnowledgeBase:
    """Read-only access to policy text, independent of the backing store."""

    def __init__(self, path: Path) -> None:
        if not path.is_file():
            raise FileNotFoundError(f"Policy knowledge base not found: {path}")
        self._content = path.read_text(encoding="utf-8").strip()

    def search(self, query: str | None = None) -> str:
        """Return policy text relevant to the query.

        The corpus is small enough to pass whole; the query is accepted so a
        real retrieval implementation can replace this without changing callers.
        """
        return self._content


@lru_cache(maxsize=1)
def get_policy_kb() -> PolicyKnowledgeBase:
    """Return the process-wide policy knowledge base singleton."""
    return PolicyKnowledgeBase(POLICIES_PATH)
