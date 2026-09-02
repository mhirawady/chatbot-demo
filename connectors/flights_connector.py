"""Mock flight information API."""

import re
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from config import FLIGHTS_PATH
from connectors.base import (
    LookupResult,
    LookupStatus,
    humanize_record,
    load_json_document,
)

_FLIGHT_NUMBER_PATTERN = re.compile(r"^[A-Z]{2}\d{1,4}$")
_AIRPORT_CODE_PATTERN = re.compile(r"^[A-Z]{3}$")
_CANCELLED_STATUS = "CANCELLED"


class FlightsConnector:
    """Looks up flight status, independent of the backing store."""

    def __init__(self, path: Path) -> None:
        document = load_json_document(path)
        records = document.get("flights")
        if not isinstance(records, list):
            raise ValueError(f"Expected a list under 'flights' in {path}")
        self._records: list[dict[str, Any]] = records
        current_time = document.get("meta", {}).get("current_time")
        self._now = datetime.fromisoformat(current_time) if current_time else None

    def find(self, flight_number: str, flight_date: str) -> LookupResult:
        """Find a flight by number and its scheduled departure date."""
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
            same_number = record["flight_number"].upper() == number
            departs_that_day = record["departure"].startswith(day)
            if same_number and departs_that_day:
                return LookupResult(
                    status=LookupStatus.FOUND, record=humanize_record(record)
                )

        return LookupResult(
            status=LookupStatus.NOT_FOUND,
            message="No flight matches that number and date.",
            details={"flight_number": number, "date": day},
        )

    def find_by_route(
        self, origin: str, destination: str, flight_date: str | None = None
    ) -> LookupResult:
        """Find non-cancelled, future flights between two airports.

        Used when a passenger's original flight was cancelled and they need
        an alternative. `flight_date` narrows the search to one day; if
        omitted, every upcoming day for the route is considered. When a date
        is given but nothing is available that day, other available dates
        for the same route are offered instead.
        """
        origin_code = origin.strip().upper()
        destination_code = destination.strip().upper()
        day = flight_date.strip() if flight_date else None

        if not _AIRPORT_CODE_PATTERN.match(origin_code):
            return LookupResult(
                status=LookupStatus.INVALID_INPUT,
                message=f"Origin must be a 3-letter airport code, got {origin!r}.",
            )
        if not _AIRPORT_CODE_PATTERN.match(destination_code):
            return LookupResult(
                status=LookupStatus.INVALID_INPUT,
                message=(
                    f"Destination must be a 3-letter airport code, got {destination!r}."
                ),
            )
        if day is not None:
            try:
                date.fromisoformat(day)
            except ValueError:
                return LookupResult(
                    status=LookupStatus.INVALID_INPUT,
                    message=f"Date must be in YYYY-MM-DD format, got {flight_date!r}.",
                )

        route_matches = [
            record
            for record in self._records
            if record["origin"].upper() == origin_code
            and record["destination"].upper() == destination_code
            and record["status"].upper() != _CANCELLED_STATUS
            and self._is_future(record["departure"])
        ]

        if day is not None:
            same_day = [r for r in route_matches if r["departure"].startswith(day)]
            if same_day:
                return LookupResult(
                    status=LookupStatus.FOUND,
                    records=[humanize_record(r) for r in same_day],
                )
            alternative_dates = sorted({r["departure"][:10] for r in route_matches})
            if alternative_dates:
                return LookupResult(
                    status=LookupStatus.NOT_FOUND,
                    message=(
                        "No available flights on that date for this route, "
                        "but other dates are available."
                    ),
                    details={"alternative_dates": alternative_dates},
                )
            return LookupResult(
                status=LookupStatus.NOT_FOUND,
                message="No available flights for that route.",
                details={"origin": origin_code, "destination": destination_code},
            )

        if route_matches:
            return LookupResult(
                status=LookupStatus.FOUND,
                records=[humanize_record(r) for r in route_matches],
            )
        return LookupResult(
            status=LookupStatus.NOT_FOUND,
            message="No available flights for that route.",
            details={"origin": origin_code, "destination": destination_code},
        )

    def _is_future(self, departure: str) -> bool:
        if self._now is None:
            return True
        return datetime.fromisoformat(departure) > self._now


@lru_cache(maxsize=1)
def get_flights_connector() -> FlightsConnector:
    """Return the process-wide flights connector singleton."""
    return FlightsConnector(FLIGHTS_PATH)
