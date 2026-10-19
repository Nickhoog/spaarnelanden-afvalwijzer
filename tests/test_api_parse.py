"""Tests voor de pure parse-functies in api.py."""

from datetime import date

import pytest

from custom_components.spaarnelanden.api import (
    Holiday,
    Notice,
    Pickup,
    SpaarnelandenResponseError,
    WasteStream,
    normalize_postcode,
    parse_addresses,
    parse_calendar,
    parse_holidays,
    parse_notices,
    parse_streams,
)

from .helpers import load


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("2011VB", "2011VB"), ("2011 vb", "2011VB"), (" 2011vb ", "2011VB")],
)
def test_normalize_postcode(raw, expected):
    assert normalize_postcode(raw) == expected


@pytest.mark.parametrize("raw", ["0123AB", "12345", "ABCD12", ""])
def test_normalize_postcode_invalid(raw):
    with pytest.raises(ValueError):
        normalize_postcode(raw)


def test_parse_addresses_labels():
    labels = {a.label for a in parse_addresses(load("addresses_multi.json"))}
    assert labels == {
        "Teststraat 1 RD, Haarlem",
        "Teststraat 1A, Haarlem",
        "Teststraat 1B, Haarlem",
    }


def test_parse_addresses_fields():
    (address,) = parse_addresses(load("addresses_single.json"))
    assert address.bag_id == "0000200000000001"
    assert address.house_number == 1
    assert address.postcode == "9999ZZ"
    assert address.label == "Teststraat 1, Haarlem"


def test_parse_addresses_empty():
    assert parse_addresses([]) == []


def test_parse_streams():
    streams = parse_streams(load("streams.json"))
    assert streams[48] == WasteStream(48, "Gft en etensresten", "gft-line")
    assert set(streams) == {56, 48, 44, 42, 39}


def test_parse_calendar_skips_invalid():
    pickups = parse_calendar(load("calendar_2026.json"))
    assert Pickup(48, date(2026, 10, 27)) in pickups
    assert len(pickups) == 6  # null en 2026-13-45 overgeslagen
    assert all(isinstance(p.date, date) for p in pickups)


def test_parse_holidays():
    assert parse_holidays(load("holidays.json")) == [
        Holiday(date(2026, 12, 25), "1e kerstdag; Milieuplein gesloten")
    ]


def test_parse_notices_strips_html():
    assert parse_notices(load("notices.json")) == [Notice(1, "Let op", "Ophaling & meer")]


@pytest.mark.parametrize(
    "fn", [parse_addresses, parse_streams, parse_calendar, parse_holidays, parse_notices]
)
def test_non_list_raises(fn):
    with pytest.raises(SpaarnelandenResponseError):
        fn({"error": "x"})
