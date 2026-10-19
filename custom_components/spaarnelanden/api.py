"""Client en parsers voor de Spaarnelanden-afvalwijzer-API.

Deze module kent geen Home Assistant-logica; ze krijgt een aiohttp-sessie mee.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date
import html
import re
from typing import Any

import aiohttp

from .const import BASE_URL, REQUEST_TIMEOUT

_POSTCODE_RE = re.compile(r"^[1-9][0-9]{3}[A-Z]{2}$")
_TAG_RE = re.compile(r"<[^>]*>")


class SpaarnelandenError(Exception):
    """Basisfout voor de Spaarnelanden-API."""


class SpaarnelandenConnectionError(SpaarnelandenError):
    """Verbinding, timeout of HTTP-fout."""


class SpaarnelandenResponseError(SpaarnelandenError):
    """Antwoord had een onverwachte vorm."""


@dataclass(frozen=True)
class Address:
    """Een adres (BAG-object) bij Spaarnelanden."""

    bag_id: str
    street: str
    house_number: int
    house_letter: str
    addition: str
    postcode: str
    city: str

    @property
    def label(self) -> str:
        """Leesbaar adres, bv. 'Teststraat 1A, Haarlem'."""
        label = f"{self.street} {self.house_number}{self.house_letter}"
        if self.addition:
            label += f" {self.addition}"
        return f"{label}, {self.city}"


@dataclass(frozen=True)
class WasteStream:
    """Een afvalstroom (soort afval)."""

    id: int
    title: str
    icon: str


@dataclass(frozen=True)
class Pickup:
    """Eén ophaalmoment van een afvalstroom."""

    stream_id: int
    date: date


@dataclass(frozen=True)
class Holiday:
    """Een feestdag of sluitingsdag."""

    date: date
    name: str


@dataclass(frozen=True)
class Notice:
    """Een actuele melding van Spaarnelanden."""

    id: int
    title: str
    text: str


def normalize_postcode(value: str) -> str:
    """Maak '2011 vb' tot '2011VB'; ValueError bij een ongeldige postcode."""
    postcode = value.replace(" ", "").upper()
    if not _POSTCODE_RE.match(postcode):
        raise ValueError(f"Ongeldige postcode: {value!r}")
    return postcode


def _require_list(data: Any) -> list[Any]:
    if not isinstance(data, list):
        raise SpaarnelandenResponseError(f"Lijst verwacht, kreeg {type(data).__name__}")
    return data


def _parse_date(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def parse_addresses(data: Any) -> list[Address]:
    """Zet het antwoord van /adressen/{postcode}-{nr} om naar adressen."""
    return [
        Address(
            bag_id=str(item["bagId"]),
            street=item.get("openbareRuimteNaam") or "",
            house_number=int(item["huisnummer"]),
            house_letter=item.get("huisletter") or "",
            addition=item.get("huisnummerToevoeging") or "",
            postcode=item.get("postcode") or "",
            city=item.get("woonplaatsNaam") or "",
        )
        for item in _require_list(data)
        if isinstance(item, dict) and item.get("bagId") and item.get("huisnummer")
    ]


def parse_streams(data: Any) -> dict[int, WasteStream]:
    """Zet het antwoord van /adressen/{bag}/afvalstromen om naar stromen per id."""
    streams: dict[int, WasteStream] = {}
    for item in _require_list(data):
        if not isinstance(item, dict) or not isinstance(item.get("id"), int):
            continue
        title = (item.get("title") or item.get("menu_title") or "").strip()
        streams[item["id"]] = WasteStream(item["id"], title, item.get("icon") or "")
    return streams


def parse_calendar(data: Any) -> list[Pickup]:
    """Zet het antwoord van /adressen/{bag}/kalender/{jaar} om naar ophaalmomenten."""
    pickups: list[Pickup] = []
    for item in _require_list(data):
        if not isinstance(item, dict) or not isinstance(item.get("afvalstroom_id"), int):
            continue
        if (pickup_date := _parse_date(item.get("ophaaldatum"))) is not None:
            pickups.append(Pickup(item["afvalstroom_id"], pickup_date))
    return pickups


def parse_holidays(data: Any) -> list[Holiday]:
    """Zet het antwoord van /feestdagen/{van}/{tot} om naar feestdagen."""
    holidays: list[Holiday] = []
    for item in _require_list(data):
        if not isinstance(item, dict):
            continue
        if (holiday_date := _parse_date(item.get("datum"))) is not None:
            holidays.append(Holiday(holiday_date, (item.get("naam") or "").strip()))
    return holidays


def parse_notices(data: Any) -> list[Notice]:
    """Zet het antwoord van /app/meldingen/{bag} om; HTML wordt gestript."""
    notices: list[Notice] = []
    for item in _require_list(data):
        if not isinstance(item, dict):
            continue
        text = html.unescape(_TAG_RE.sub("", item.get("content") or "")).strip()
        if text:
            notices.append(Notice(item.get("id"), (item.get("kop") or "").strip(), text))
    return notices


class SpaarnelandenClient:
    """Async client voor afvalwijzer.spaarnelanden.nl."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        """Gebruik de gedeelde aiohttp-sessie van Home Assistant."""
        self._session = session

    async def _get_json(self, path: str) -> Any:
        url = f"{BASE_URL}{path}"
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                response = await self._session.get(url)
                if response.status >= 400:
                    raise SpaarnelandenConnectionError(f"HTTP {response.status} voor {url}")
                return await response.json(content_type=None)
        except (TimeoutError, aiohttp.ClientError) as err:
            raise SpaarnelandenConnectionError(f"Fout bij ophalen {url}: {err}") from err
        except ValueError as err:
            raise SpaarnelandenResponseError(f"Geen geldige JSON van {url}") from err

    async def lookup_addresses(self, postcode: str, house_number: int) -> list[Address]:
        """Zoek adressen bij postcode + huisnummer (ValueError bij ongeldige postcode)."""
        postcode = normalize_postcode(postcode)
        return parse_addresses(await self._get_json(f"/adressen/{postcode}-{house_number}"))

    async def get_streams(self, bag_id: str) -> dict[int, WasteStream]:
        """Haal alle afvalstromen van een adres op."""
        return parse_streams(await self._get_json(f"/adressen/{bag_id}/afvalstromen"))

    async def get_calendar(self, bag_id: str, year: int) -> list[Pickup]:
        """Haal de jaarkalender van een adres op."""
        return parse_calendar(await self._get_json(f"/adressen/{bag_id}/kalender/{year}"))

    async def get_holidays(self, start: date, end: date) -> list[Holiday]:
        """Haal feestdagen en sluitingen op tussen start en end."""
        return parse_holidays(
            await self._get_json(f"/feestdagen/{start.isoformat()}/{end.isoformat()}")
        )

    async def get_notices(self, bag_id: str) -> list[Notice]:
        """Haal actuele meldingen voor een adres op."""
        return parse_notices(await self._get_json(f"/app/meldingen/{bag_id}"))
