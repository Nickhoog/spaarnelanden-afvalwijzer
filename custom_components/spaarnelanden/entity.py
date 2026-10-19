"""Gemeenschappelijke basis voor Spaarnelanden-entities."""

from __future__ import annotations

from datetime import date, datetime

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .api import WasteStream
from .const import CONF_LABEL, DOMAIN
from .coordinator import SpaarnelandenCoordinator


def today() -> date:
    """De datum van vandaag in de tijdzone van Home Assistant."""
    return dt_util.now().date()


def stream_for(coordinator: SpaarnelandenCoordinator, stream_id: int) -> WasteStream:
    """De afvalstroom bij een id, met een nette naam als de API hem niet kent."""
    return coordinator.data.streams.get(
        stream_id, WasteStream(stream_id, f"Afvalstroom {stream_id}", "")
    )


class SpaarnelandenEntity(CoordinatorEntity[SpaarnelandenCoordinator]):
    """Basis-entity: één apparaat per adres, status opnieuw schrijven na middernacht."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SpaarnelandenCoordinator, key: str) -> None:
        """Initialiseer met een unieke sleutel binnen het adres."""
        super().__init__(coordinator)
        bag_id = coordinator.bag_id
        self._attr_unique_id = f"{bag_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, bag_id)},
            name=f"Spaarnelanden {coordinator.config_entry.data[CONF_LABEL]}",
            # Expliciet leeg: onofficiële integratie, en v0.1.0 zette hier nog
            # "Spaarnelanden" in het apparaatregister.
            manufacturer=None,
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def available(self) -> bool:
        """Beschikbaar zolang er data is; de kalender blijft maanden geldig.

        Een mislukte verversing laat de laatst geladen gegevens dus staan in plaats van
        alles 12 uur onbeschikbaar te maken.
        """
        return self.coordinator.data is not None

    async def async_added_to_hass(self) -> None:
        """Registreer de middernacht-update."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_time_change(
                self.hass, self._handle_midnight, hour=0, minute=0, second=1
            )
        )

    @callback
    def _handle_midnight(self, _now: datetime) -> None:
        self.async_write_ha_state()
