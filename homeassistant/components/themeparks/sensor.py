"""Platform for sensor integration."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import TIME_MINUTES
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.httpx_client import get_async_client

# from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""

    children_url = (
        "https://api.themeparks.wiki/v1/entity/"
        + config_entry.data["parkslug"]
        + "/children"
    )

    client = get_async_client(hass)
    response = await client.request(
        "GET",
        children_url,
        timeout=10,
        follow_redirects=True,
    )

    children_data = response.json()

    def filter_child(item):
        return item["entityType"] == "SHOW" or item["entityType"] == "ATTRACTION"

    def parse_child(item):
        """Parse children from API into AttractionSensors.

            Children are like:
            {
            "id": "2d2b5083-3cb4-453f-b067-4fec48322195",
            "name": "Disney Illuminations",
            "entityType": "SHOW",
            "slug": null,
            "externalId": "P1GS24"
        }
        """
        return AttractionSensor(item["name"], item["id"])

    async_add_entities(
        map(parse_child, filter(filter_child, children_data["children"]))
    )


class AttractionSensor(SensorEntity):
    """Representation of a Sensor."""

    _attr_name = "UNKNOWN"
    _attr_native_unit_of_measurement = TIME_MINUTES
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, name, api_id):
        """Create new sensor for the attraction wait time."""
        self._api_id = api_id
        self._attr_name = name

    # def update(self) -> None:
    #     """Fetch new state data for the sensor.
    #     This is the only method that should fetch new data for Home Assistant.
    #     """
    #     self._attr_native_value = 23
