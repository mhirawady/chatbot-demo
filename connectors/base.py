"""Shared result types for mock API connectors."""

import json
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class LookupStatus(StrEnum):
    """Outcome of a connector lookup."""

    FOUND = "found"
    NOT_FOUND = "not_found"
    INVALID_INPUT = "invalid_input"


@dataclass(frozen=True)
class LookupResult:
    """Normalized connector response returned to tool handlers."""

    status: LookupStatus
    record: dict[str, Any] | None = None
    message: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        """Render the result as a JSON-serializable payload for the model."""
        payload: dict[str, Any] = {"status": self.status.value}
        if self.record is not None:
            payload["record"] = self.record
        if self.message is not None:
            payload["message"] = self.message
        if self.details:
            payload["details"] = self.details
        return payload


def load_json_records(path: Path, key: str) -> list[dict[str, Any]]:
    """Read a list of records from a mock data file."""
    if not path.is_file():
        raise FileNotFoundError(f"Mock data file not found: {path}")
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    records = data.get(key)
    if not isinstance(records, list):
        raise ValueError(f"Expected a list under '{key}' in {path}")
    return records
