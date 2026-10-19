"""Tests voor de sensoren."""

from datetime import date

import pytest
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from homeassistant.util import dt as dt_util

from custom_components.spaarnelanden.api import Pickup, parse_calendar
from custom_components.spaarnelanden.const import DEFAULT_ICON

from .helpers import PREFIX, load, make_client, setup_integration

GFT = f"sensor.{PREFIX}_gft_en_etensresten"
REST = f"sensor.{PREFIX}_restafval"
RECYCLE = f"sensor.{PREFIX}_recyclewagen"
TODAY = f"sensor.{PREFIX}_vandaag"
TOMORROW = f"sensor.{PREFIX}_morgen"
NOTICES = f"sensor.{PREFIX}_meldingen"


@pytest.fixture(autouse=True)
async def amsterdam(hass):
    await hass.config.async_set_time_zone("Europe/Amsterdam")
    hass.config.language = "nl"


@pytest.fixture
def client():
    return make_client()


async def setup_at(hass, freezer, client, moment: str):
    freezer.move_to(moment)
    await setup_integration(hass, client)


async def test_waste_sensor_next_date(hass, freezer, client):
    await setup_at(hass, freezer, client, "2026-10-26 20:00:00+01:00")
    state = hass.states.get(GFT)
    assert state.state == "2026-10-27"
    assert state.attributes["dagen_tot"] == 1
    assert state.attributes["afvalstroom_id"] == 48
    assert state.attributes["afvalsoort"] == "Gft en etensresten"
    assert state.attributes["icon"] == "mdi:leaf"
    assert state.attributes["device_class"] == "date"


async def test_only_streams_with_pickups(hass, freezer, client):
    await setup_at(hass, freezer, client, "2026-10-26 20:00:00+01:00")
    assert hass.states.get(f"sensor.{PREFIX}_papier_en_karton") is None
    assert hass.states.get(RECYCLE) is not None


async def test_tomorrow_and_today(hass, freezer, client):
    await setup_at(hass, freezer, client, "2026-10-26 20:00:00+01:00")
    assert hass.states.get(TOMORROW).state == "Gft en etensresten"
    assert hass.states.get(TOMORROW).attributes["afvalsoorten"] == ["Gft en etensresten"]
    assert hass.states.get(TODAY).state == "Geen"
    assert hass.states.get(TODAY).attributes["afvalsoorten"] == []


async def test_two_types_joined(hass, freezer, client):
    await setup_at(hass, freezer, client, "2026-10-28 20:00:00+01:00")
    assert (
        hass.states.get(TOMORROW).state
        == "Plastic, blik, drinkpakken & papier (duobak), Restafval"
    )


async def test_notices_sensor(hass, freezer, client):
    await setup_at(hass, freezer, client, "2026-10-26 20:00:00+01:00")
    state = hass.states.get(NOTICES)
    assert state.state == "1"
    assert state.attributes["meldingen"] == [{"titel": "Let op", "tekst": "Ophaling & meer"}]


async def test_midnight_rollover(hass, freezer, client):
    await setup_at(hass, freezer, client, "2026-10-26 20:00:00+01:00")
    calls = client.get_streams.await_count
    freezer.move_to("2026-10-27 00:00:02+01:00")
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
    assert hass.states.get(GFT).attributes["dagen_tot"] == 0
    assert hass.states.get(TODAY).state == "Gft en etensresten"
    assert client.get_streams.await_count == calls


async def test_today_uses_local_timezone(hass, freezer, client):
    await setup_at(hass, freezer, client, "2026-10-26T23:30:00+00:00")
    assert hass.states.get(GFT).attributes["dagen_tot"] == 0


async def test_next_date_from_next_year(hass, freezer, client):
    await setup_at(hass, freezer, client, "2026-12-31 12:00:00+01:00")
    assert hass.states.get(REST).state == "2027-01-07"


async def test_unknown_stream_id_fallback(hass, freezer, client):
    calendar = parse_calendar(load("calendar_2026.json")) + [Pickup(99, date(2026, 11, 2))]
    client.get_calendar.side_effect = lambda bag, year: calendar if year == 2026 else []
    await setup_at(hass, freezer, client, "2026-10-26 20:00:00+01:00")
    state = hass.states.get(f"sensor.{PREFIX}_afvalstroom_99")
    assert state.state == "2026-11-02"
    assert state.attributes["icon"] == DEFAULT_ICON


async def test_no_future_date_unknown(hass, freezer, client):
    await setup_at(hass, freezer, client, "2026-11-05 12:00:00+01:00")
    assert hass.states.get(RECYCLE).state == "unknown"


async def test_failed_refresh_keeps_last_data(hass, freezer, client):
    """Eén mislukte verversing maakt de entities niet onbeschikbaar."""
    from datetime import timedelta

    from custom_components.spaarnelanden.api import SpaarnelandenConnectionError

    await setup_at(hass, freezer, client, "2026-10-26 08:00:00+01:00")
    client.get_streams.side_effect = SpaarnelandenConnectionError
    freezer.tick(timedelta(hours=12, minutes=1))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
    assert client.get_streams.await_count == 2
    assert hass.states.get(GFT).state == "2026-10-27"
    assert hass.states.get(TOMORROW).state == "Gft en etensresten"
