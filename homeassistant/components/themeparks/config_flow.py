"""Config flow for Theme Park Wait Times integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries

# from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.httpx_client import get_async_client

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {vol.Required("parkslug"): str, vol.Required("parkname"): str}
)


# async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
#     """Validate the user input allows us to connect.

#     Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
#     """
#     return data


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Theme Park Wait Times."""

    VERSION = 1
    _destinations: dict[str, Any] = {}

    async def _async_update_data(self):
        """Fetch list of parks."""

        client = get_async_client(self.hass)
        response = await client.request(
            "GET",
            "https://api.themeparks.wiki/v1/destinations",
            timeout=10,
            follow_redirects=True,
        )

        parkdata = response.json()

        def parse_dest(item):
            slug = item["slug"]
            name = item["name"]
            return (name, slug)

        return dict(map(parse_dest, parkdata["destinations"]))

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Run the user config flow step."""

        if user_input is not None:

            return self.async_create_entry(
                title="Theme Park: " + user_input["parkname"],
                data={
                    "parkslug": self._destinations[user_input["parkname"]],
                    "parkname": user_input["parkname"],
                },
            )

        if self._destinations == {}:
            self._destinations = await self._async_update_data()

        schema = {vol.Required("parkname"): vol.In(sorted(self._destinations.keys()))}
        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(schema), last_step=True
        )
