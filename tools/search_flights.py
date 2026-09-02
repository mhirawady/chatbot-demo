"""Flight route search tool, for finding alternatives to a cancelled flight."""

from typing import Any

from connectors import get_flights_connector
from connectors.base import API_TERMINOLOGY_NOTE
from tools.registry import register_tool

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "origin": {
            "type": "string",
            "description": "Origin airport code, e.g. DEN.",
        },
        "destination": {
            "type": "string",
            "description": "Destination airport code, e.g. SFO.",
        },
        "date": {
            "type": "string",
            "description": (
                "Preferred departure date in YYYY-MM-DD format. Omit to see "
                "every upcoming date for this route."
            ),
        },
    },
    "required": ["origin", "destination"],
    "additionalProperties": False,
}


@register_tool("search_flights", SCHEMA, extra_description=API_TERMINOLOGY_NOTE)
def search_flights(
    origin: str, destination: str, date: str | None = None
) -> dict[str, Any]:
    """Search for non-cancelled, future SkyHop flights between two airports.

    Use this to offer alternatives when a passenger's flight is cancelled.
    If no flights are available on the requested date, other available
    dates for the same route are returned instead.
    """
    result = get_flights_connector().find_by_route(origin, destination, date)
    return result.to_payload()
