"""Mock flight information API."""

import re
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

from config import FLIGHTS_PATH
from connectors.base import LookupResult, LookupStatus, load_json_records

_FLIGHT_NUMBER_PATTERN = re.compile(r"^[A-Z]{2}\d{1,4}$")


class FlightsConnector:
    """Looks up flight status, independent of the backing store."""

    def __init__(self, path: Path) -> None:
        self._records: list[dict[str, Any]] = load_json_records(path, "flights")

    def find(self, flight_number: str, flight_date: str) -> LookupResult:
        """Find a flight by number and ISO date."""
        number = flight_number.strip().upper().replace(" ", "")
        day = flight_date.strip()

        if not _FLIGHT_NUMBER_PATTERN.match(number):
            return LookupResult(
                status=LookupStatus.INVALID_INPUT,
                message=(
                    "Flight number must be two letters followed by 1-4 digits, "
                    f"got {flight_number!r}."
                ),
            )
        try:
            date.fromisoformat(day)
        except ValueError:
            return LookupResult(
                status=LookupStatus.INVALID_INPUT,
                message=f"Date must be in YYYY-MM-DD format, got {flight_date!r}.",
            )

        for record in self._records:
            if record["flight_number"].upper() == number and record["date"] == day:
                return LookupResult(status=LookupStatus.FOUND, record=record)

        return LookupResult(
            status=LookupStatus.NOT_FOUND,
            message="No flight matches that number and date.",
            details={"flight_number": number, "date": day},
        )


@lru_cache(maxsize=1)
def get_flights_connector() -> FlightsConnector:
    """Return the process-wide flights connector singleton."""
    return FlightsConnector(FLIGHTS_PATH)
