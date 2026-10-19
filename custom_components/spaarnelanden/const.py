"""Constanten voor de Spaarnelanden-integratie."""

from datetime import timedelta

from homeassistant.const import Platform

DOMAIN = "spaarnelanden"

BASE_URL = "https://afvalwijzer.spaarnelanden.nl/rest"
UPDATE_INTERVAL = timedelta(hours=12)
REQUEST_TIMEOUT = 30

PLATFORMS = [Platform.SENSOR, Platform.CALENDAR]

CONF_BAG_ID = "bag_id"
CONF_POSTCODE = "postcode"
CONF_HOUSE_NUMBER = "house_number"
CONF_LABEL = "label"

ICON_MAP = {
    "gft-line": "mdi:leaf",
    "rest2-line": "mdi:trash-can",
    "duocontainer-line": "mdi:recycle",
    "recyclewagen-line": "mdi:truck",
    "papier-line": "mdi:newspaper",
    "pbd-line": "mdi:bottle-soda",
    "glas-line": "mdi:glass-fragile",
}
DEFAULT_ICON = "mdi:trash-can-outline"
