"""Spaarnelanden afvalkalender voor Home Assistant."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SpaarnelandenClient
from .const import PLATFORMS
from .coordinator import SpaarnelandenConfigEntry, SpaarnelandenCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: SpaarnelandenConfigEntry) -> bool:
    """Zet een adres op."""
    client = SpaarnelandenClient(async_get_clientsession(hass))
    coordinator = SpaarnelandenCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SpaarnelandenConfigEntry) -> bool:
    """Verwijder een adres."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
