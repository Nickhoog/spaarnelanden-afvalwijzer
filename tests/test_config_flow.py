"""Tests voor de config flow."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.spaarnelanden.api import (
    SpaarnelandenConnectionError,
    SpaarnelandenResponseError,
    parse_addresses,
)
from custom_components.spaarnelanden.const import DOMAIN

from .helpers import BAG, load

COMPONENT = Path(__file__).parent.parent / "custom_components" / "spaarnelanden"
LOOKUP = "custom_components.spaarnelanden.config_flow.SpaarnelandenClient.lookup_addresses"
USER_INPUT = {"postcode": "9999 zz", "house_number": 1}


@pytest.fixture(autouse=True)
def no_setup():
    """Voorkom dat de entry na aanmaken echt wordt opgezet."""
    with patch(
        "custom_components.spaarnelanden.async_setup_entry", return_value=True, create=True
    ):
        yield


async def start(hass):
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )


async def test_single_address_creates_entry(hass):
    result = await start(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    with patch(LOOKUP, AsyncMock(return_value=parse_addresses(load("addresses_single.json")))):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Teststraat 1, Haarlem"
    assert result["data"] == {
        "bag_id": BAG,
        "postcode": "9999ZZ",
        "house_number": 1,
        "label": "Teststraat 1, Haarlem",
    }
    assert result["result"].unique_id == BAG


async def test_multiple_addresses_sorted(hass):
    result = await start(hass)
    with patch(LOOKUP, AsyncMock(return_value=parse_addresses(load("addresses_multi.json")))):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "select_address"
        selector = result["data_schema"].schema["bag_id"]
        labels = [o["label"] for o in selector.config["options"]]
        assert labels == [
            "Teststraat 1 RD, Haarlem",
            "Teststraat 1A, Haarlem",
            "Teststraat 1B, Haarlem",
        ]
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"bag_id": "0000200000000002"}
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Teststraat 1A, Haarlem"
    assert result["data"]["bag_id"] == "0000200000000002"


async def test_invalid_postcode(hass):
    result = await start(hass)
    with patch(LOOKUP, AsyncMock()) as lookup:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"postcode": "12345", "house_number": 1}
        )
    assert result["errors"] == {"postcode": "invalid_postcode"}
    lookup.assert_not_called()


async def test_address_not_found(hass):
    result = await start(hass)
    with patch(LOOKUP, AsyncMock(return_value=[])):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["errors"] == {"base": "address_not_found"}


@pytest.mark.parametrize("exc", [SpaarnelandenConnectionError, SpaarnelandenResponseError])
async def test_cannot_connect(hass, exc):
    result = await start(hass)
    with patch(LOOKUP, AsyncMock(side_effect=exc)):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["errors"] == {"base": "cannot_connect"}


async def test_duplicate_aborts(hass):
    MockConfigEntry(domain=DOMAIN, unique_id=BAG, data={"bag_id": BAG}).add_to_hass(hass)
    result = await start(hass)
    with patch(LOOKUP, AsyncMock(return_value=parse_addresses(load("addresses_single.json")))):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


def _keys(obj, prefix=""):
    if isinstance(obj, dict):
        return {k for key, val in obj.items() for k in _keys(val, f"{prefix}{key}.")}
    return {prefix.rstrip(".")}


@pytest.mark.parametrize("lang", ["en", "nl"])
def test_translations_match_strings(lang):
    strings = json.loads((COMPONENT / "strings.json").read_text(encoding="utf-8"))
    translation = json.loads(
        (COMPONENT / "translations" / f"{lang}.json").read_text(encoding="utf-8")
    )
    assert _keys(translation) == _keys(strings)
