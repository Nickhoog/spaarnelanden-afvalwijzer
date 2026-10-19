"""Tests voor SpaarnelandenClient (HTTP gemockt met aioclient_mock)."""

from datetime import date

import aiohttp
import pytest

from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.spaarnelanden.api import (
    SpaarnelandenClient,
    SpaarnelandenConnectionError,
    SpaarnelandenResponseError,
)
from custom_components.spaarnelanden.const import BASE_URL

from .helpers import BAG, load

STREAMS_URL = f"{BASE_URL}/adressen/{BAG}/afvalstromen"
NOTICES_URL = f"{BASE_URL}/app/meldingen/{BAG}"


def client(hass) -> SpaarnelandenClient:
    return SpaarnelandenClient(async_get_clientsession(hass))


async def test_lookup_addresses_url(hass, aioclient_mock):
    aioclient_mock.get(f"{BASE_URL}/adressen/9999ZZ-1", json=load("addresses_multi.json"))
    assert len(await client(hass).lookup_addresses("9999 zz", 1)) == 3


async def test_lookup_addresses_invalid_postcode(hass, aioclient_mock):
    with pytest.raises(ValueError):
        await client(hass).lookup_addresses("12345", 1)
    assert aioclient_mock.call_count == 0


async def test_get_streams_url(hass, aioclient_mock):
    aioclient_mock.get(STREAMS_URL, json=load("streams.json"))
    assert 48 in await client(hass).get_streams(BAG)


async def test_get_calendar_url(hass, aioclient_mock):
    aioclient_mock.get(
        f"{BASE_URL}/adressen/{BAG}/kalender/2026", json=load("calendar_2026.json")
    )
    assert len(await client(hass).get_calendar(BAG, 2026)) == 6


async def test_get_holidays_url(hass, aioclient_mock):
    aioclient_mock.get(f"{BASE_URL}/feestdagen/2026-01-01/2027-12-31", json=load("holidays.json"))
    assert await client(hass).get_holidays(date(2026, 1, 1), date(2027, 12, 31))


async def test_get_notices_url(hass, aioclient_mock):
    aioclient_mock.get(NOTICES_URL, json=load("notices.json"))
    assert len(await client(hass).get_notices(BAG)) == 1


async def test_timeout_raises_connection_error(hass, aioclient_mock):
    aioclient_mock.get(STREAMS_URL, exc=TimeoutError)
    with pytest.raises(SpaarnelandenConnectionError):
        await client(hass).get_streams(BAG)


async def test_client_error_raises_connection_error(hass, aioclient_mock):
    aioclient_mock.get(STREAMS_URL, exc=aiohttp.ClientError)
    with pytest.raises(SpaarnelandenConnectionError):
        await client(hass).get_streams(BAG)


async def test_http_500_raises_connection_error(hass, aioclient_mock):
    aioclient_mock.get(STREAMS_URL, status=500)
    with pytest.raises(SpaarnelandenConnectionError):
        await client(hass).get_streams(BAG)


async def test_html_response_raises_response_error(hass, aioclient_mock):
    aioclient_mock.get(
        NOTICES_URL,
        text="<!doctype html><html></html>",
        headers={"Content-Type": "text/html"},
    )
    with pytest.raises(SpaarnelandenResponseError):
        await client(hass).get_notices(BAG)


async def test_non_list_raises_response_error(hass, aioclient_mock):
    aioclient_mock.get(STREAMS_URL, json={"error": "x"})
    with pytest.raises(SpaarnelandenResponseError):
        await client(hass).get_streams(BAG)
