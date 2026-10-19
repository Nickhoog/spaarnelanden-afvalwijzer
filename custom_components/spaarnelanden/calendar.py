"""Kalenders: ophaaldata en feestdagen/sluitingen."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .coordinator import SpaarnelandenConfigEntry, SpaarnelandenCoordinator
from .entity import SpaarnelandenEntity, stream_for, today


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SpaarnelandenConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Maak de twee kalenders aan voor één adres."""
    coordinator = entry.runtime_data
    async_add_entities([WasteCalendar(coordinator), HolidayCalendar(coordinator)])


def _all_day(day: date, summary: str) -> CalendarEvent:
    return CalendarEvent(start=day, end=day + timedelta(days=1), summary=summary)


class _SpaarnelandenCalendar(SpaarnelandenEntity, CalendarEntity):
    """Gedeelde logica: hele-dag-events uit coordinator-data."""

    def _events(self) -> list[CalendarEvent]:
        raise NotImplementedError

    @property
    def event(self) -> CalendarEvent | None:
        """Het eerstvolgende event vanaf vandaag."""
        now = today()
        return next((e for e in self._events() if e.start >= now), None)

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Events die overlappen met het gevraagde venster (einde exclusief)."""
        return [
            e
            for e in self._events()
            if dt_util.start_of_local_day(e.start) < end_date
            and dt_util.start_of_local_day(e.end) > start_date
        ]


class WasteCalendar(_SpaarnelandenCalendar):
    """Alle ophaalmomenten van dit en volgend jaar."""

    _attr_translation_key = "waste"

    def __init__(self, coordinator: SpaarnelandenCoordinator) -> None:
        """Initialiseer de afvalkalender."""
        super().__init__(coordinator, "calendar")

    def _events(self) -> list[CalendarEvent]:
        return [
            _all_day(p.date, stream_for(self.coordinator, p.stream_id).title)
            for p in self.coordinator.data.pickups
        ]


class HolidayCalendar(_SpaarnelandenCalendar):
    """Feestdagen en sluitingen van Spaarnelanden."""

    _attr_translation_key = "holidays"

    def __init__(self, coordinator: SpaarnelandenCoordinator) -> None:
        """Initialiseer de feestdagenkalender."""
        super().__init__(coordinator, "holidays")

    def _events(self) -> list[CalendarEvent]:
        return [_all_day(h.date, h.name) for h in self.coordinator.data.holidays]
