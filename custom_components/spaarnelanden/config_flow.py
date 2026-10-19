"""Config flow voor Spaarnelanden: postcode + huisnummer, eventueel adreskeuze."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
)

from .api import Address, SpaarnelandenClient, SpaarnelandenError, normalize_postcode
from .const import CONF_BAG_ID, CONF_HOUSE_NUMBER, CONF_LABEL, CONF_POSTCODE, DOMAIN

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_POSTCODE): str,
        vol.Required(CONF_HOUSE_NUMBER): vol.All(vol.Coerce(int), vol.Range(min=1)),
    }
)


class SpaarnelandenConfigFlow(ConfigFlow, domain=DOMAIN):
    """Voeg een adres toe."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialiseer de flow."""
        self._addresses: dict[str, Address] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Vraag postcode en huisnummer."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                postcode = normalize_postcode(user_input[CONF_POSTCODE])
            except ValueError:
                errors[CONF_POSTCODE] = "invalid_postcode"
            else:
                client = SpaarnelandenClient(async_get_clientsession(self.hass))
                try:
                    addresses = await client.lookup_addresses(
                        postcode, user_input[CONF_HOUSE_NUMBER]
                    )
                except SpaarnelandenError:
                    errors["base"] = "cannot_connect"
                else:
                    if not addresses:
                        errors["base"] = "address_not_found"
                    elif len(addresses) == 1:
                        return await self._async_create(addresses[0])
                    else:
                        self._addresses = {a.bag_id: a for a in addresses}
                        return await self.async_step_select_address()

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(USER_SCHEMA, user_input),
            errors=errors,
        )

    async def async_step_select_address(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Laat kiezen bij meerdere adressen op hetzelfde huisnummer."""
        if user_input is not None:
            return await self._async_create(self._addresses[user_input[CONF_BAG_ID]])

        options = [
            SelectOptionDict(value=a.bag_id, label=a.label)
            for a in sorted(self._addresses.values(), key=lambda a: a.label)
        ]
        return self.async_show_form(
            step_id="select_address",
            data_schema=vol.Schema(
                {vol.Required(CONF_BAG_ID): SelectSelector(SelectSelectorConfig(options=options))}
            ),
        )

    async def _async_create(self, address: Address) -> ConfigFlowResult:
        await self.async_set_unique_id(address.bag_id)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=address.label,
            data={
                CONF_BAG_ID: address.bag_id,
                CONF_POSTCODE: address.postcode,
                CONF_HOUSE_NUMBER: address.house_number,
                CONF_LABEL: address.label,
            },
        )
