"""DataUpdateCoordinator voor Spaarnelanden."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import (
    Holiday,
    Notice,
    Pickup,
    SpaarnelandenClient,
    SpaarnelandenError,
    WasteStream,
)
from .const import CONF_BAG_ID, DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

type SpaarnelandenConfigEntry = ConfigEntry[SpaarnelandenCoordinator]


@dataclass
class SpaarnelandenData:
    """Alle opgehaalde gegevens voor één adres."""

    streams: dict[int, WasteStream]
    pickups: list[Pickup]
    holidays: list[Holiday]
    notices: list[Notice]


class SpaarnelandenCoordinator(DataUpdateCoordinator[SpaarnelandenData]):
    """Haalt elke 12 uur kalender, feestdagen en meldingen op."""

    config_entry: SpaarnelandenConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, client: SpaarnelandenClient
    ) -> None:
        """Initialiseer de coordinator voor één config entry."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.client = client
        self.bag_id: str = entry.data[CONF_BAG_ID]

    async def _async_update_data(self) -> SpaarnelandenData:
        year = dt_util.now().year
        try:
            streams = await self.client.get_streams(self.bag_id)
            pickups = await self.client.get_calendar(self.bag_id, year)
        except SpaarnelandenError as err:
            raise UpdateFailed(f"Ophalen afvalkalender mislukt: {err}") from err

        try:
            pickups = pickups + await self.client.get_calendar(self.bag_id, year + 1)
        except SpaarnelandenError as err:
            _LOGGER.debug("Kalender %s niet beschikbaar: %s", year + 1, err)

        try:
            holidays = await self.client.get_holidays(date(year, 1, 1), date(year + 1, 12, 31))
        except SpaarnelandenError as err:
            _LOGGER.debug("Feestdagen niet beschikbaar: %s", err)
            holidays = []

        try:
            notices = await self.client.get_notices(self.bag_id)
        except SpaarnelandenError as err:
            _LOGGER.debug("Meldingen niet beschikbaar: %s", err)
            notices = []

        return SpaarnelandenData(
            streams=streams,
            pickups=sorted(set(pickups), key=lambda p: (p.date, p.stream_id)),
            holidays=sorted(holidays, key=lambda h: h.date),
            notices=notices,
        )
