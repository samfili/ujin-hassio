"""The Ujin Smart Home integration."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import TokenExpiredError, UjinApiClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SWITCH,
]

SCAN_INTERVAL = timedelta(seconds=30)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Ujin from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Create API client
    api_client = UjinApiClient(
        email=entry.data[CONF_EMAIL],
        session=None,  # Will be created by the client
    )

    # Restore token and area_guid from saved data
    if "token" in entry.data:
        api_client._token = entry.data["token"]
        _LOGGER.info("Restored token for %s", entry.data[CONF_EMAIL])

    if "area_guid" in entry.data:
        api_client._area_guid = entry.data["area_guid"]
        _LOGGER.info("Restored area_guid: %s", entry.data["area_guid"])

    # Validate token by fetching devices
    try:
        _LOGGER.info("Validating token for %s", entry.data[CONF_EMAIL])
        devices = await api_client.get_devices()
        if not devices:
            _LOGGER.warning("No devices found, but token seems valid")
    except Exception as err:
        _LOGGER.error("Failed to validate token: %s", err)
        # Token might be expired, user needs to re-configure
        from .api import TokenExpiredError
        if isinstance(err, TokenExpiredError):
            _LOGGER.error(
                "Token expired for %s. Please reconfigure the integration.",
                entry.data[CONF_EMAIL]
            )
            # The integration will continue but coordinator will fail
            # User will see "Unavailable" status
        return False

    # Create coordinator
    async def async_update_data():
        """Fetch data from API."""
        try:
            devices = await api_client.get_devices()
            _LOGGER.debug("Fetched %d devices from Ujin API", len(devices))
            return devices
        except TokenExpiredError as err:
            _LOGGER.error("Token expired: %s", err)
            raise UpdateFailed(
                "Token expired. Please reconfigure the integration."
            ) from err
        except Exception as err:
            _LOGGER.error("Error communicating with API: %s", err)
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=async_update_data,
        update_interval=SCAN_INTERVAL,
    )

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "api": api_client,
        "coordinator": coordinator,
    }

    # Setup platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
