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


async def test_device_not_attributed_to_spaarnelanden(hass):
    """Onofficiële integratie: het apparaat mag niet 'door Spaarnelanden' tonen."""
    from homeassistant.helpers import device_registry as dr

    entry = await setup_integration(hass, make_client())
    (device,) = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)
    assert device.manufacturer is None


async def test_existing_manufacturer_is_cleared(hass):
    """Bestaande apparaten uit v0.1.0 hadden manufacturer 'Spaarnelanden'; die moet weg."""
    from homeassistant.helpers import device_registry as dr

    from custom_components.spaarnelanden.const import DOMAIN

    from .helpers import BAG, make_entry

    entry = make_entry()
    entry.add_to_hass(hass)
    registry = dr.async_get(hass)
    registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, BAG)},
        manufacturer="Spaarnelanden",
    )
    from unittest.mock import patch

    with patch("custom_components.spaarnelanden.SpaarnelandenClient", return_value=make_client()):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    (device,) = dr.async_entries_for_config_entry(registry, entry.entry_id)
    assert device.manufacturer is None
