"""Support for Ujin lights."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ujin lights from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    api = hass.data[DOMAIN][entry.entry_id]["api"]

    # Parse devices and create light entities
    lights = []
    if coordinator.data:
        for device in coordinator.data:
            # TODO: Adjust based on actual device structure from API
            if device.get("type") == "light":
                lights.append(UjinLight(coordinator, api, device))

    async_add_entities(lights)


class UjinLight(CoordinatorEntity, LightEntity):
    """Representation of a Ujin light."""

    def __init__(self, coordinator, api, device: dict[str, Any]) -> None:
        """Initialize the light."""
        super().__init__(coordinator)
        self._api = api
        self._device = device
        self._attr_unique_id = device.get("id")
        self._attr_name = device.get("name", "Ujin Light")

        # Determine color mode based on device capabilities
        # TODO: Update based on actual device capabilities from API
        if device.get("supports_brightness"):
            self._attr_color_mode = ColorMode.BRIGHTNESS
            self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
        else:
            self._attr_color_mode = ColorMode.ONOFF
            self._attr_supported_color_modes = {ColorMode.ONOFF}

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        # TODO: Update based on actual device state structure
        return self._device.get("state", False)

    @property
    def brightness(self) -> int | None:
        """Return the brightness of the light."""
        # TODO: Update based on actual device state structure
        if self.color_mode == ColorMode.BRIGHTNESS:
            # Convert from API format (0-100) to HA format (0-255)
            api_brightness = self._device.get("brightness", 100)
            return int(api_brightness * 255 / 100)
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light."""
        brightness = kwargs.get(ATTR_BRIGHTNESS)

        # TODO: Update based on actual API requirements
        state_data = {"state": True}
        if brightness is not None:
            # Convert from HA format (0-255) to API format (0-100)
            state_data["brightness"] = int(brightness * 100 / 255)

        await self._api.set_device_state(self._attr_unique_id, state_data)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the light."""
        # TODO: Update based on actual API requirements
        await self._api.set_device_state(self._attr_unique_id, {"state": False})
        await self.coordinator.async_request_refresh()
