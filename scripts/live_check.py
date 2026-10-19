"""Live controle tegen de echte Spaarnelanden-API.

Gebruik: uv run python scripts/live_check.py POSTCODE HUISNUMMER [BAG_ID]

Het adres komt alleen uit de argumenten; sla de uitvoer niet op in de repo.
"""

import asyncio
from collections import Counter
from datetime import date
from pathlib import Path
import sys

import aiohttp

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from custom_components.spaarnelanden.api import SpaarnelandenClient  # noqa: E402


async def main(postcode: str, house_number: int, bag_id: str | None) -> None:
    async with aiohttp.ClientSession() as session:
        client = SpaarnelandenClient(session)
        addresses = await client.lookup_addresses(postcode, house_number)
        print(f"Adressen gevonden: {len(addresses)}")
        for address in addresses:
            print(f"  {address.bag_id}  {address.label}")
        if not addresses:
            return
        bag = bag_id or addresses[0].bag_id
        year = date.today().year
        streams = await client.get_streams(bag)
        pickups = await client.get_calendar(bag, year)
        next_year = await client.get_calendar(bag, year + 1)
        today = date.today()
        print(f"\nKalender {year}: {len(pickups)} ophalingen, {year + 1}: {len(next_year)}")
        for stream_id, count in sorted(Counter(p.stream_id for p in pickups).items()):
            upcoming = [p.date for p in pickups + next_year if p.stream_id == stream_id and p.date >= today]
            title = streams[stream_id].title if stream_id in streams else f"Afvalstroom {stream_id}"
            print(f"  {title}: {count}x, eerstvolgende {min(upcoming) if upcoming else '-'}")
        holidays = await client.get_holidays(date(year, 1, 1), date(year + 1, 12, 31))
        print(f"\nFeestdagen: {len(holidays)}")
        for holiday in holidays[:5]:
            print(f"  {holiday.date}  {holiday.name}")
        notices = await client.get_notices(bag)
        print(f"\nMeldingen: {len(notices)}")
        for notice in notices:
            print(f"  {notice.title}: {notice.text[:80]}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], int(sys.argv[2]), sys.argv[3] if len(sys.argv) > 3 else None))
