"""Het dashboardvoorbeeld uit de README moet echt werken."""

from pathlib import Path
import re

import pytest
import yaml

from homeassistant.helpers.template import Template

from .helpers import make_client, setup_integration

README = Path(__file__).parent.parent / "README.md"


def readme_card() -> dict:
    blocks = re.findall(r"```yaml\n(.*?)```", README.read_text(encoding="utf-8"), re.S)
    (card,) = [yaml.safe_load(b) for b in blocks if "type: markdown" in b]
    return card


@pytest.fixture(autouse=True)
async def amsterdam(hass, freezer):
    await hass.config.async_set_time_zone("Europe/Amsterdam")
    freezer.move_to("2026-10-26 20:00:00+01:00")


async def test_readme_dashboard_card_lists_pickups_in_order(hass):
    await setup_integration(hass, make_client())
    content = readme_card()["content"]
    rendered = Template(content, hass).async_render(parse_result=False)
    lines = [line.strip() for line in rendered.splitlines() if line.strip()]
    assert lines == [
        "- **Gft en etensresten**: morgen",
        "- **Plastic, blik, drinkpakken & papier (duobak)**: over 3 dagen",
        "- **Restafval**: over 3 dagen",
        "- **Recyclewagen**: over 9 dagen",
    ]
