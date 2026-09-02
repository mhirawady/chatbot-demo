"""Flight status lookup tool."""

from typing import Any

from connectors import get_flights_connector
from connectors.base import API_TERMINOLOGY_NOTE
from tools.registry import register_tool

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "flight_number": {
            "type": "string",
            "description": "Flight number including the airline code, e.g. SH412.",
        },
        "date": {
            "type": "string",
            "description": "Scheduled departure date in YYYY-MM-DD format.",
        },
    },
    "required": ["flight_number", "date"],
    "additionalProperties": False,
}


@register_tool("get_flight_status", SCHEMA, extra_description=API_TERMINOLOGY_NOTE)
def get_flight_status(flight_number: str, date: str) -> dict[str, Any]:
    """Look up the status of a SkyHop flight by flight number and date.

    Returns scheduled departure/arrival, status, aircraft, and seat availability.
    """
    result = get_flights_connector().find(flight_number, date)
    return result.to_payload()
