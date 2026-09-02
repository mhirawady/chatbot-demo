"""Connector and knowledge base interface tests."""

from connectors import get_bookings_connector, get_flights_connector
from connectors.base import LookupStatus
from knowledge_base import get_policy_kb


def test_booking_lookup_is_case_insensitive() -> None:
    result = get_bookings_connector().find(" mr8zt5 ", "nakamura")
    assert result.status is LookupStatus.FOUND
    assert result.record is not None
    assert result.record["fare_type"] == "Business"


def test_booking_lookup_rejects_malformed_reference() -> None:
    result = get_bookings_connector().find("MR-7", "Alvarez")
    assert result.status is LookupStatus.INVALID_INPUT


def test_booking_lookup_rejects_empty_last_name() -> None:
    result = get_bookings_connector().find("MR7QX2", "   ")
    assert result.status is LookupStatus.INVALID_INPUT


def test_booking_lookup_requires_matching_last_name() -> None:
    result = get_bookings_connector().find("MR7QX2", "Nakamura")
    assert result.status is LookupStatus.NOT_FOUND


def test_flight_lookup_normalizes_flight_number() -> None:
    result = get_flights_connector().find("mr 418", "2026-09-04")
    assert result.status is LookupStatus.FOUND
    assert result.record is not None
    assert result.record["gate"] == "B12"


def test_flight_lookup_rejects_non_iso_date() -> None:
    result = get_flights_connector().find("MR418", "Sept 4 2026")
    assert result.status is LookupStatus.INVALID_INPUT


def test_flight_lookup_not_found_for_wrong_date() -> None:
    result = get_flights_connector().find("MR418", "2026-12-25")
    assert result.status is LookupStatus.NOT_FOUND


def test_lookup_payload_omits_missing_fields() -> None:
    payload = get_flights_connector().find("MR418", "2026-09-04").to_payload()
    assert payload["status"] == "found"
    assert "message" not in payload


def test_policy_kb_returns_policy_text() -> None:
    content = get_policy_kb().search("baggage")
    assert "Meridian Airlines" in content
    assert "Checked baggage allowance" in content


def test_policy_kb_is_query_independent_for_now() -> None:
    kb = get_policy_kb()
    assert kb.search("baggage") == kb.search("refunds")
