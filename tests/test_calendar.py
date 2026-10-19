"""Tests voor de kalender-entities."""

import pytest

from homeassistant.components.calendar import DOMAIN as CALENDAR_DOMAIN

from .helpers import PREFIX, make_client, setup_integration

WASTE = f"calendar.{PREFIX}_afvalkalender"
HOLIDAYS = f"calendar.{PREFIX}_feestdagen_en_sluitingen"


@pytest.fixture(autouse=True)
async def setup(hass, freezer):
    await hass.config.async_set_time_zone("Europe/Amsterdam")
    hass.config.language = "nl"
    freezer.move_to("2026-10-26 10:00:00+01:00")
    await setup_integration(hass, make_client())


async def get_events(hass, entity_id, start, end):
    result = await hass.services.async_call(
        CALENDAR_DOMAIN,
        "get_events",
        {"entity_id": entity_id, "start_date_time": start, "end_date_time": end},
        blocking=True,
        return_response=True,
    )
    return result[entity_id]["events"]


async def test_waste_calendar_state(hass):
    state = hass.states.get(WASTE)
    assert state.attributes["message"] == "Gft en etensresten"
    assert state.attributes["start_time"].startswith("2026-10-27")
    assert state.attributes["all_day"] is True


async def test_get_events_window(hass):
    events = await get_events(hass, WASTE, "2026-10-29 00:00:00", "2026-10-30 23:59:59")
    assert sorted(e["summary"] for e in events) == [
        "Plastic, blik, drinkpakken & papier (duobak)",
        "Restafval",
    ]
    assert all(e["start"] == "2026-10-29" and e["end"] == "2026-10-30" for e in events)


async def test_events_span_next_year(hass):
    events = await get_events(hass, WASTE, "2027-01-01 00:00:00", "2027-01-31 00:00:00")
    assert [e["start"] for e in events] == ["2027-01-05", "2027-01-07"]


async def test_holiday_calendar(hass):
    state = hass.states.get(HOLIDAYS)
    assert state.attributes["message"] == "1e kerstdag; Milieuplein gesloten"
    assert state.attributes["start_time"].startswith("2026-12-25")


async def test_holidays_not_in_waste_calendar(hass):
    events = await get_events(hass, WASTE, "2026-12-25 00:00:00", "2026-12-25 23:59:59")
    assert events == []


async def test_window_end_is_exclusive(hass):
    """Venster tot middernacht mag de events van de volgende dag niet bevatten."""
    events = await get_events(hass, WASTE, "2026-10-28 00:00:00", "2026-10-29 00:00:00")
    assert events == []


async def test_window_start_mid_day_includes_that_day(hass):
    events = await get_events(hass, WASTE, "2026-10-27 15:00:00", "2026-10-27 16:00:00")
    assert [e["summary"] for e in events] == ["Gft en etensresten"]
