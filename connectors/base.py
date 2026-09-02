"""Shared result types for mock API connectors."""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

# Appended to tool descriptions so the LLM knows how to talk about the data
# it gets back, since terminology/formatting are fixed here, not by the model.
API_TERMINOLOGY_NOTE = (
    'Terminology: the internal field "PNR" is called a "booking code" or '
    '"reservation code" when speaking with a passenger — never say "PNR" to '
    "them. Every date and time in the response is already formatted for "
    'human reading (for example "Tuesday Sep 1, 2026 3:14PM"); read it as-is '
    "and do not reformat, reparse, or convert it."
)

_ISO_DATETIME_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
_ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


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


def _humanize_datetime(value: str) -> str:
    """Render an ISO date/datetime as e.g. 'Tuesday Sep 1, 2026 3:14PM'."""
    if _ISO_DATETIME_PATTERN.match(value):
        parsed = datetime.fromisoformat(value)
        formatted = parsed.strftime("%A %b %-d, %Y %-I:%M%p")
        return formatted
    if _ISO_DATE_PATTERN.match(value):
        parsed_date = datetime.fromisoformat(value)
        return parsed_date.strftime("%A %b %-d, %Y")
    return value


def humanize_record(value: Any) -> Any:
    """Recursively rewrite ISO date/time strings for passenger-facing output.

    Applied to every mock API record before it reaches the model, so the
    "read it as-is" instruction in API_TERMINOLOGY_NOTE is always true.
    """
    if isinstance(value, dict):
        return {key: humanize_record(item) for key, item in value.items()}
    if isinstance(value, list):
        return [humanize_record(item) for item in value]
    if isinstance(value, str):
        return _humanize_datetime(value)
    return value


def rename_key(record: dict[str, Any], old_key: str, new_key: str) -> dict[str, Any]:
    """Return a copy of record with old_key renamed to new_key, if present."""
    if old_key not in record:
        return record
    renamed = dict(record)
    renamed[new_key] = renamed.pop(old_key)
    return renamed
