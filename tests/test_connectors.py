"""Connector and knowledge base interface tests."""

from connectors import get_bookings_connector, get_flights_connector
from connectors.base import LookupStatus
from knowledge_base import get_policy_kb


def test_booking_lookup_is_case_insensitive() -> None:
    result = get_bookings_connector().find(" gh7x2p ", "webb")
    assert result.status is LookupStatus.FOUND
    assert result.record is not None
    assert result.record["segments"][0]["flight_number"] == "SH412"


def test_booking_lookup_rejects_malformed_code() -> None:
    result = get_bookings_connector().find("GH-7", "Webb")
    assert result.status is LookupStatus.INVALID_INPUT


def test_booking_lookup_rejects_empty_last_name() -> None:
    result = get_bookings_connector().find("GH7X2P", "   ")
    assert result.status is LookupStatus.INVALID_INPUT


def test_booking_lookup_requires_matching_last_name() -> None:
    result = get_bookings_connector().find("GH7X2P", "Sharma")
    assert result.status is LookupStatus.NOT_FOUND


def test_booking_lookup_renames_pnr_to_booking_code() -> None:
    result = get_bookings_connector().find("GH7X2P", "Webb")
    assert result.record is not None
    assert result.record["booking_code"] == "GH7X2P"
    assert "pnr" not in result.record


def test_booking_lookup_humanizes_created_timestamp() -> None:
    result = get_bookings_connector().find("GH7X2P", "Webb")
    assert result.record is not None
    assert result.record["created"] == "Sunday Jun 14, 2026 10:22AM"


def test_flight_lookup_normalizes_flight_number() -> None:
    result = get_flights_connector().find("sh 412", "2026-07-09")
    assert result.status is LookupStatus.FOUND
    assert result.record is not None
    assert result.record["origin"] == "DEN"


def test_flight_lookup_rejects_non_iso_date() -> None:
    result = get_flights_connector().find("SH412", "Jul 9 2026")
    assert result.status is LookupStatus.INVALID_INPUT


def test_flight_lookup_not_found_for_wrong_date() -> None:
    result = get_flights_connector().find("SH412", "2026-12-25")
    assert result.status is LookupStatus.NOT_FOUND


def test_flight_lookup_humanizes_departure_and_arrival() -> None:
    result = get_flights_connector().find("SH412", "2026-07-09")
    assert result.record is not None
    assert result.record["departure"] == "Thursday Jul 9, 2026 6:45PM"
    assert result.record["arrival"] == "Thursday Jul 9, 2026 8:25PM"


def test_lookup_payload_omits_missing_fields() -> None:
    payload = get_flights_connector().find("SH412", "2026-07-09").to_payload()
    assert payload["status"] == "found"
    assert "message" not in payload


def test_route_search_excludes_cancelled_and_past_flights() -> None:
    result = get_flights_connector().find_by_route("DEN", "SFO")
    assert result.status is LookupStatus.FOUND
    assert result.records is not None
    flight_numbers = {r["flight_number"] for r in result.records}
    assert flight_numbers == {"TN2205", "SH420", "SH424"}


def test_route_search_is_case_insensitive() -> None:
    result = get_flights_connector().find_by_route("den", "sfo")
    assert result.status is LookupStatus.FOUND


def test_route_search_filters_by_date() -> None:
    result = get_flights_connector().find_by_route("DEN", "SFO", "2026-07-10")
    assert result.status is LookupStatus.FOUND
    assert result.records is not None
    flight_numbers = {r["flight_number"] for r in result.records}
    assert flight_numbers == {"SH420", "SH424"}


def test_route_search_offers_alternative_dates_when_requested_date_has_none() -> None:
    result = get_flights_connector().find_by_route("DEN", "SFO", "2026-07-15")
    assert result.status is LookupStatus.NOT_FOUND
    assert result.details["alternative_dates"] == ["2026-07-09", "2026-07-10"]


def test_route_search_not_found_for_unserved_route() -> None:
    result = get_flights_connector().find_by_route("DEN", "MIA")
    assert result.status is LookupStatus.NOT_FOUND
    assert "alternative_dates" not in result.details


def test_route_search_rejects_bad_airport_code() -> None:
    result = get_flights_connector().find_by_route("DENV", "SFO")
    assert result.status is LookupStatus.INVALID_INPUT


def test_route_search_humanizes_departure_times() -> None:
    result = get_flights_connector().find_by_route("DEN", "SFO", "2026-07-10")
    assert result.records is not None
    departures = {r["departure"] for r in result.records}
    assert "Friday Jul 10, 2026 7:05AM" in departures


def test_policy_kb_returns_policy_text() -> None:
    content = get_policy_kb().search("baggage")
    assert "SkyHop Airlines" in content
    assert "Involuntary rebooking" in content


def test_policy_kb_is_query_independent_for_now() -> None:
    kb = get_policy_kb()
    assert kb.search("baggage") == kb.search("refunds")
