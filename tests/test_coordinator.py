"""Tests voor SpaarnelandenCoordinator."""

from datetime import date

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.spaarnelanden.api import (
    Pickup,
    SpaarnelandenConnectionError,
    parse_calendar,
)
from custom_components.spaarnelanden.const import CONF_BAG_ID, DOMAIN
from custom_components.spaarnelanden.coordinator import SpaarnelandenCoordinator

from .helpers import BAG, load, make_client


@pytest.fixture
def client():
    return make_client()


@pytest.fixture
def coordinator(hass, client, freezer):
    freezer.move_to("2026-12-30 12:00:00+01:00")
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_BAG_ID: BAG}, unique_id=BAG)
    entry.add_to_hass(hass)
    return SpaarnelandenCoordinator(hass, entry, client)


async def test_merges_next_year(coordinator, client):
    data = await coordinator._async_update_data()
    assert data.pickups == sorted(data.pickups, key=lambda p: (p.date, p.stream_id))
    assert data.pickups.count(Pickup(48, date(2027, 1, 5))) == 1
    assert Pickup(42, date(2027, 1, 7)) in data.pickups
    client.get_calendar.assert_any_await(BAG, 2026)
    client.get_calendar.assert_any_await(BAG, 2027)
    client.get_holidays.assert_awaited_with(date(2026, 1, 1), date(2027, 12, 31))
    assert len(data.notices) == 1
    assert 48 in data.streams


async def test_optional_notices_failure_ignored(coordinator, client):
    client.get_notices.side_effect = SpaarnelandenConnectionError
    data = await coordinator._async_update_data()
    assert data.notices == []
    assert data.pickups


async def test_optional_holidays_failure_ignored(coordinator, client):
    client.get_holidays.side_effect = SpaarnelandenConnectionError
    data = await coordinator._async_update_data()
    assert data.holidays == []


async def test_optional_next_year_failure_ignored(coordinator, client):
    current = parse_calendar(load("calendar_2026.json"))

    async def calendar(bag, year):
        if year == 2027:
            raise SpaarnelandenConnectionError
        return current

    client.get_calendar.side_effect = calendar
    data = await coordinator._async_update_data()
    assert Pickup(42, date(2027, 1, 7)) not in data.pickups
    assert Pickup(48, date(2026, 10, 27)) in data.pickups


async def test_streams_failure_raises_update_failed(coordinator, client):
    client.get_streams.side_effect = SpaarnelandenConnectionError
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_current_year_failure_raises_update_failed(coordinator, client):
    async def calendar(bag, year):
        if year == 2026:
            raise SpaarnelandenConnectionError
        return []

    client.get_calendar.side_effect = calendar
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


def test_bag_id(coordinator):
    assert coordinator.bag_id == BAG
