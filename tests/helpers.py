"""Hulpfuncties voor de tests."""

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant

from custom_components.spaarnelanden.api import (
    SpaarnelandenClient,
    parse_calendar,
    parse_holidays,
    parse_notices,
    parse_streams,
)
from custom_components.spaarnelanden.const import DOMAIN

FIXTURES = Path(__file__).parent / "fixtures"
BAG = "0000200000000001"
LABEL = "Teststraat 1, Haarlem"
PREFIX = "spaarnelanden_teststraat_1_haarlem"


def load(name: str) -> Any:
    """Laad een JSON-fixture."""
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def make_client() -> AsyncMock:
    """Gemockte client die de fixtures teruggeeft."""
    client = AsyncMock(spec=SpaarnelandenClient)
    client.get_streams.return_value = parse_streams(load("streams.json"))
    calendars = {
        2026: parse_calendar(load("calendar_2026.json")),
        2027: parse_calendar(load("calendar_2027.json")),
        2028: [],
    }
    client.get_calendar.side_effect = lambda bag, year: calendars[year]
    client.get_holidays.return_value = parse_holidays(load("holidays.json"))
    client.get_notices.return_value = parse_notices(load("notices.json"))
    return client


def make_entry() -> MockConfigEntry:
    """Config entry voor het testadres."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=LABEL,
        unique_id=BAG,
        data={"bag_id": BAG, "postcode": "9999ZZ", "house_number": 1, "label": LABEL},
    )


async def setup_integration(hass: HomeAssistant, client: AsyncMock) -> MockConfigEntry:
    """Zet de integratie op met een gemockte client."""
    entry = make_entry()
    entry.add_to_hass(hass)
    with patch("custom_components.spaarnelanden.SpaarnelandenClient", return_value=client):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry
