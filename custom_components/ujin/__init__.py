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
from .websocket import UjinWebSocketClient

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

    # Restore token, user_token and area_guid from saved data
    if "token" in entry.data:
        api_client._token = entry.data["token"]
        _LOGGER.info("Restored token for %s", entry.data[CONF_EMAIL])

    if "user_token" in entry.data:
        api_client._user_token = entry.data["user_token"]
        _LOGGER.info("Restored user_token: %s...", entry.data["user_token"][:20] if entry.data["user_token"] else "None")

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

    # Setup WebSocket for real-time updates
    websocket_client = None
    try:
        wss_url = await api_client.get_websocket_url()
        if wss_url:
            def handle_websocket_message(data: dict) -> None:
                """Handle incoming WebSocket message."""
                try:
                    # WebSocket messages contain device updates
                    # Update coordinator data without API call
                    if "data" in data:
                        # Parse device updates from WebSocket message
                        # This will be called from async context, safe to update coordinator
                        hass.async_create_task(coordinator.async_request_refresh())
                except Exception as err:
                    _LOGGER.error("Error handling WebSocket message: %s", err)

            websocket_client = UjinWebSocketClient(
                url=wss_url,
                on_message=handle_websocket_message,
            )
            # Connect to WebSocket
            await websocket_client.connect()
            _LOGGER.info("WebSocket real-time updates enabled")
        else:
            _LOGGER.warning("WebSocket URL not available, using polling only")
    except Exception as err:
        _LOGGER.error("Failed to setup WebSocket: %s. Falling back to polling.", err)

    hass.data[DOMAIN][entry.entry_id] = {
        "api": api_client,
        "coordinator": coordinator,
        "websocket": websocket_client,
    }

    # Setup platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        # Disconnect WebSocket if active
        entry_data = hass.data[DOMAIN].pop(entry.entry_id)
        if websocket_client := entry_data.get("websocket"):
            await websocket_client.disconnect()
            _LOGGER.info("WebSocket disconnected")

    return unload_ok
