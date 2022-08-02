"""The Theme Park Wait Times integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.httpx_client import get_async_client

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Theme Park Wait Times from a config entry."""
    data = hass.data.setdefault(DOMAIN, {})

    api = ThemeParkAPI(hass, entry)
    await api.async_initialize()

    data[entry.entry_id] = api

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        connections=None,
        name=entry.title,
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class ThemeParkAPI:
    """Wrapper for theme parks API."""

    # -- Set in async_initialize --
    ha_device_registry: dr.DeviceRegistry
    ha_entity_registry: er.EntityRegistry

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the gateway."""
        self._hass = hass
        self._config_entry = config_entry
        self._parkslug = config_entry.data["parkslug"]
        self._parkname = config_entry.data["parkname"]

    async def async_initialize(self) -> None:
        """Initialize controller and connect radio."""
        self.ha_device_registry = dr.async_get(self._hass)
        self.ha_entity_registry = er.async_get(self._hass)

    async def do_live_lookup(self):
        """Do API lookup of the 'live' page of this park."""
        _LOGGER.info("Running do_live_lookup in ThemeParkAPI")

        items = await self.do_api_lookup("live", "liveData")

        def parse_live(item):
            """Parse live data from API.

            LiveData is like:
            {
                "id": "f0d4b531-e291-471b-9527-00410c2bbd65",
                "name": "Crush's Coaster",
                "entityType": "ATTRACTION",
                "parkId": "ca888437-ebb4-4d50-aed2-d227f7096968",
                "externalId": "P2XA03",
                "queue": {
                    "STANDBY": {
                        "waitTime": 85
                    },
                    "SINGLE_RIDER": {
                        "waitTime": 75
                    },
                    "PAID_RETURN_TIME": {
                        "price": {
                        "amount": 1800,
                        "currency": "EUR"
                        },
                        "state": "FINISHED",
                        "returnEnd": null,
                        "returnStart": null
                    }
                },
                "status": "OPERATING",
                "lastUpdated": "2022-07-27T17:39:49Z"
            },
            """

            _LOGGER.info("Parsed API item for: %s", item["name"])

            name = item["name"] + " (" + self._parkname + ")"

            if "queue" not in item:
                _LOGGER.info("No queue in item")
                return (item["id"], {"api_id": item["id"], "name": name, "time": None})

            if "STANDBY" not in item["queue"]:
                _LOGGER.info("No STANDBY in item['queue']")
                return (item["id"], {"api_id": item["id"], "name": name, "time": None})

            _LOGGER.info("Time found")
            return (
                item["id"],
                {
                    "api_id": item["id"],
                    "name": name,
                    "time": item["queue"]["STANDBY"]["waitTime"],
                },
            )

        return dict(map(parse_live, items))

    async def do_api_lookup(self, subpage, subfield):
        """Lookup the subpage and subfield in the API."""
        url = "https://api.themeparks.wiki/v1/entity/" + self._parkslug + "/" + subpage

        client = get_async_client(self._hass)
        response = await client.request(
            "GET",
            url,
            timeout=30,
            follow_redirects=True,
        )

        items_data = response.json()

        def filter_item(item):
            return item["entityType"] == "SHOW" or item["entityType"] == "ATTRACTION"

        return filter(filter_item, items_data[subfield])
