"""Tests voor setup en unload."""

from homeassistant.config_entries import ConfigEntryState

from custom_components.spaarnelanden.api import SpaarnelandenConnectionError

from .helpers import make_client, setup_integration


async def test_setup_and_unload(hass):
    entry = await setup_integration(hass, make_client())
    assert entry.state is ConfigEntryState.LOADED
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_setup_retry_on_error(hass):
    client = make_client()
    client.get_streams.side_effect = SpaarnelandenConnectionError
    entry = await setup_integration(hass, client)
    assert entry.state is ConfigEntryState.SETUP_RETRY
