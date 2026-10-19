"""Sensoren: per afvalsoort, vandaag, morgen en meldingen."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DEFAULT_ICON, ICON_MAP
from .coordinator import SpaarnelandenConfigEntry, SpaarnelandenCoordinator
from .entity import SpaarnelandenEntity, stream_for, today

NONE_TEXT = "Geen"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SpaarnelandenConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Maak de sensoren aan voor één adres."""
    coordinator = entry.runtime_data
    stream_ids = sorted({p.stream_id for p in coordinator.data.pickups})
    entities: list[SensorEntity] = [
        WasteTypeSensor(coordinator, stream_id) for stream_id in stream_ids
    ]
    entities += [
        DaySensor(coordinator, 0, "today"),
        DaySensor(coordinator, 1, "tomorrow"),
        NoticesSensor(coordinator),
    ]
    async_add_entities(entities)


class WasteTypeSensor(SpaarnelandenEntity, SensorEntity):
    """Eerstvolgende ophaaldatum van één afvalsoort."""

    _attr_device_class = SensorDeviceClass.DATE

    def __init__(self, coordinator: SpaarnelandenCoordinator, stream_id: int) -> None:
        """Initialiseer voor één afvalstroom."""
        super().__init__(coordinator, str(stream_id))
        self._stream_id = stream_id
        stream = stream_for(coordinator, stream_id)
        self._attr_name = stream.title
        self._attr_icon = ICON_MAP.get(stream.icon, DEFAULT_ICON)

    def _next_date(self) -> date | None:
        now = today()
        return next(
            (
                p.date
                for p in self.coordinator.data.pickups
                if p.stream_id == self._stream_id and p.date >= now
            ),
            None,
        )

    @property
    def native_value(self) -> date | None:
        """Eerstvolgende ophaaldatum."""
        return self._next_date()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Dagen tot ophalen en de afvalsoort."""
        next_date = self._next_date()
        return {
            "dagen_tot": (next_date - today()).days if next_date else None,
            "afvalsoort": stream_for(self.coordinator, self._stream_id).title,
            "afvalstroom_id": self._stream_id,
        }


class DaySensor(SpaarnelandenEntity, SensorEntity):
    """Welke afvalsoorten vandaag of morgen worden opgehaald."""

    def __init__(
        self, coordinator: SpaarnelandenCoordinator, offset: int, translation_key: str
    ) -> None:
        """Initialiseer met een dag-offset (0 = vandaag, 1 = morgen)."""
        super().__init__(coordinator, translation_key)
        self._offset = offset
        self._attr_translation_key = translation_key
        self._attr_icon = "mdi:delete-clock"

    def _titles(self) -> list[str]:
        day = today() + timedelta(days=self._offset)
        return sorted(
            stream_for(self.coordinator, p.stream_id).title
            for p in self.coordinator.data.pickups
            if p.date == day
        )

    @property
    def native_value(self) -> str:
        """Afvalsoorten, gescheiden door komma's, of 'Geen'."""
        return ", ".join(self._titles()) or NONE_TEXT

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """De afvalsoorten als lijst."""
        return {"afvalsoorten": self._titles()}


class NoticesSensor(SpaarnelandenEntity, SensorEntity):
    """Aantal actuele meldingen van Spaarnelanden."""

    _attr_translation_key = "notices"
    _attr_icon = "mdi:information-outline"

    def __init__(self, coordinator: SpaarnelandenCoordinator) -> None:
        """Initialiseer de meldingen-sensor."""
        super().__init__(coordinator, "notices")

    @property
    def native_value(self) -> int:
        """Aantal meldingen."""
        return len(self.coordinator.data.notices)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """De meldingen met titel en tekst."""
        return {
            "meldingen": [
                {"titel": n.title, "tekst": n.text} for n in self.coordinator.data.notices
            ]
        }
