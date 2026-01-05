"""Switch platform for Ujin Smart Home."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ujin switches from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    api = hass.data[DOMAIN][entry.entry_id]["api"]

    entities = []
    devices = coordinator.data

    for device in devices:
        # All devices with switch control type
        controls = device.get("controls", [])
        if controls and controls[0].get("type") == "switch":
            entities.append(
                UjinSwitch(
                    coordinator=coordinator,
                    api=api,
                    device_data=device,
                )
            )

    async_add_entities(entities)


class UjinSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a Ujin Switch."""

    def __init__(self, coordinator, api, device_data: dict[str, Any]) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._api = api
        self._device_data = device_data
        self._attr_unique_id = f"{device_data['id']}_{device_data['signal']}"
        self._attr_name = device_data["name"]

    @property
    def device_info(self):
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self._device_data["id"])},
            "name": self._device_data["device_name"],
            "manufacturer": self._device_data.get("specification", "Ujin"),
            "model": self._device_data.get("model_title", "Unknown"),
        }

    @property
    def is_on(self) -> bool:
        """Return True if entity is on."""
        # Find current device in coordinator data
        for device in self.coordinator.data:
            if (
                device["id"] == self._device_data["id"]
                and device["signal"] == self._device_data["signal"]
            ):
                controls = device.get("controls", [])
                if controls:
                    return controls[0].get("value", 0) == 1
        return False

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        for device in self.coordinator.data:
            if (
                device["id"] == self._device_data["id"]
                and device["signal"] == self._device_data["signal"]
            ):
                return device.get("status") == "ok"
        return False

    @property
    def icon(self) -> str:
        """Return the icon to use in the frontend."""
        svg = self._device_data.get("svg", "")
        category = self._device_data.get("category_name", "")

        # Map SVG names to MDI icons
        icon_map = {
            "light": "mdi:lightbulb",
            "electricSockets": "mdi:power-socket",
            "waterController": "mdi:water-pump",
        }

        if svg in icon_map:
            return icon_map[svg]
        elif "вода" in category.lower() or "aqua" in self._attr_name.lower():
            return "mdi:water-pump"
        elif "освещение" in self._attr_name.lower():
            return "mdi:lightbulb"
        elif "розетк" in self._attr_name.lower():
            return "mdi:power-socket"
        else:
            return "mdi:toggle-switch"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        for device in self.coordinator.data:
            if (
                device["id"] == self._device_data["id"]
                and device["signal"] == self._device_data["signal"]
            ):
                return {
                    "device_id": device["id"],
                    "signal": device["signal"],
                    "status": device.get("status_title", "Unknown"),
                    "room": device.get("room", {}).get("title", "Unknown"),
                    "model": device.get("model", "Unknown"),
                    "category": device.get("category_name", "Unknown"),
                    "socket_enabled": device.get("socket_enabled", False),
                    "local_ip": device.get("management", {})
                    .get("local", {})
                    .get("ip", "N/A"),
                }
        return {}

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        _LOGGER.info("Turning ON %s (ID: %s, Signal: %s)",
                    self._attr_name,
                    self._device_data["id"],
                    self._device_data["signal"])

        success = await self._api.send_device_command(
            device_id=self._device_data["id"],
            signal=self._device_data["signal"],
            state=1,
        )

        if success:
            # Immediately update local state for instant UI feedback
            if self._device_data.get("controls"):
                self._device_data["controls"][0]["value"] = 1
            # Write state to Home Assistant immediately to update history
            self.async_write_ha_state()
        else:
            _LOGGER.error("Failed to turn on %s", self._attr_name)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        _LOGGER.info("Turning OFF %s (ID: %s, Signal: %s)",
                    self._attr_name,
                    self._device_data["id"],
                    self._device_data["signal"])

        success = await self._api.send_device_command(
            device_id=self._device_data["id"],
            signal=self._device_data["signal"],
            state=0,
        )

        if success:
            # Immediately update local state for instant UI feedback
            if self._device_data.get("controls"):
                self._device_data["controls"][0]["value"] = 0
            # Write state to Home Assistant immediately to update history
            self.async_write_ha_state()
        else:
            _LOGGER.error("Failed to turn off %s", self._attr_name)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
