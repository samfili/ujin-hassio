"""Ujin API Client."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .const import (
    API_APP_PARAM,
    API_AUTH_EMAIL_SEND,
    API_AUTH_EMAIL_VERIFY,
    API_AUTH_USER,
    API_BASE_URL,
    API_DEVICES_MAIN,
    API_DEVICES_WSS,
    API_PLATFORM_PARAM,
    API_PROFILE_OBJECTS,
    API_SEND_SIGNAL,
    HEADER_APP_LANG,
    HEADER_APP_PLATFORM,
    HEADER_APP_TYPE,
    HEADER_APP_VERSION,
)

_LOGGER = logging.getLogger(__name__)


class TokenExpiredError(Exception):
    """Exception raised when API token has expired."""
    pass


class UjinApiClient:
    """Ujin API Client."""

    def __init__(
        self,
        email: str,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        """Initialize the API client."""
        self.email = email
        self._session = session
        self._token: str | None = None  # Main auth token
        self._user_token: str | None = None  # Apartment-specific token
        self._area_guid: str | None = None
        self._base_url = API_BASE_URL

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    async def send_auth_code(self) -> dict[str, Any]:
        """Send authentication code to email."""
        session = await self._get_session()

        try:
            url = f"{self._base_url}{API_AUTH_EMAIL_SEND}"
            payload = {
                "email": self.email,
                "app": API_APP_PARAM,
                "platform": API_PLATFORM_PARAM,
            }
            headers = {
                HEADER_APP_TYPE: "mobile",
                HEADER_APP_PLATFORM: API_PLATFORM_PARAM,
                HEADER_APP_LANG: "ru-RU",
                HEADER_APP_VERSION: "2",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }

            async with session.post(url, json=payload, headers=headers) as response:
                data = await response.json()
                if data.get("error") == 0:
                    _LOGGER.info("Auth code sent to %s, wait time: %s sec",
                                self.email, data.get("data", {}).get("time", 0))
                    return data
                else:
                    _LOGGER.error("Failed to send auth code: %s", data.get("message"))
                    return data
        except Exception as err:
            _LOGGER.error("Error sending auth code: %s", err)
            raise

    async def verify_auth_code(self, code: str) -> bool:
        """Verify authentication code and get token."""
        session = await self._get_session()

        try:
            url = f"{self._base_url}{API_AUTH_EMAIL_VERIFY}"
            payload = {
                "email": self.email,
                "code": code,
                "app": API_APP_PARAM,
                "platform": API_PLATFORM_PARAM,
            }
            headers = {
                HEADER_APP_TYPE: "mobile",
                HEADER_APP_PLATFORM: API_PLATFORM_PARAM,
                HEADER_APP_LANG: "ru-RU",
                HEADER_APP_VERSION: "2",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }

            async with session.post(url, json=payload, headers=headers) as response:
                data = await response.json()
                if data.get("error") == 0:
                    self._token = data.get("data", {}).get("token")
                    _LOGGER.info("Successfully authenticated with Ujin API")

                    # Get user profile to retrieve area_guid
                    await self._get_user_profile()
                    return True
                else:
                    _LOGGER.error("Auth verification failed: %s", data.get("message"))
                    return False
        except Exception as err:
            _LOGGER.error("Error verifying auth code: %s", err)
            raise

    async def _get_user_profile(self) -> None:
        """Get user profile and extract area_guid."""
        session = await self._get_session()

        try:
            url = f"{self._base_url}{API_AUTH_USER}"
            params = {
                "token": self._token,
                "app": API_APP_PARAM,
                "platform": API_PLATFORM_PARAM,
            }

            async with session.get(url, params=params) as response:
                data = await response.json()
                _LOGGER.info("User profile retrieved")

            # Get apartments to extract area_guid
            await self._get_apartments()
        except Exception as err:
            _LOGGER.error("Error getting user profile: %s", err)

    async def _get_apartments(self) -> list[dict[str, Any]]:
        """Get list of apartments/flats and extract area_guid."""
        if not self._token:
            _LOGGER.error("Not authenticated")
            return []

        session = await self._get_session()

        try:
            url = f"{self._base_url}{API_PROFILE_OBJECTS}"
            params = {
                "token": self._token,
                "app": API_APP_PARAM,
                "platform": API_PLATFORM_PARAM,
            }

            async with session.get(url, params=params) as response:
                data = await response.json()
                _LOGGER.debug("Profile objects response: %s", data)

                if data.get("error") is None or data.get("error") == 0:
                    # Extract apartments from response
                    apartments = []
                    for complex_data in data.get("data", []):
                        items = complex_data.get("items", [])
                        apartments.extend(items)

                    _LOGGER.info("Found %d apartment(s)", len(apartments))

                    # Use first apartment's area_guid and user_token
                    if apartments:
                        if not self._area_guid:
                            self._area_guid = apartments[0].get("area_guid")
                            _LOGGER.info("Extracted area_guid: %s from apartment '%s'",
                                        self._area_guid, apartments[0].get("title", "Unknown"))

                        if not self._user_token:
                            # Try user_token first, fallback to dpr_user_token
                            self._user_token = apartments[0].get("user_token") or apartments[0].get("dpr_user_token")
                            if self._user_token:
                                _LOGGER.info("Extracted user_token: %s... from apartment",
                                            self._user_token[:20] if self._user_token else "None")

                    return apartments
                else:
                    _LOGGER.error("Failed to get apartments: %s", data.get("message"))
                    return []
        except Exception as err:
            _LOGGER.error("Error getting apartments: %s", err)
            return []

    async def get_devices(self) -> list[dict[str, Any]]:
        """Get all devices from Ujin API."""
        if not self._token:
            _LOGGER.error("Not authenticated. Call verify_auth_code first.")
            return []

        session = await self._get_session()

        # Use apartment user_token if available, otherwise fallback to main token
        token_to_use = self._user_token if self._user_token else self._token
        _LOGGER.debug("Using token for devices request: %s...", token_to_use[:20] if token_to_use else "None")

        try:
            url = f"{self._base_url}{API_DEVICES_MAIN}"
            params = {
                "token": token_to_use,
                "app": API_APP_PARAM,
                "platform": API_PLATFORM_PARAM,
                "co2": "1",
                "lang": "ru-RU",
            }

            # Add area_guid if available
            if self._area_guid:
                params["area_guid"] = self._area_guid

            async with session.get(url, params=params) as response:
                data = await response.json()
                _LOGGER.debug("API Response: %s", data)

                if data.get("error") == 0:
                    devices_data = data.get("data", {}).get("devices", [])
                    _LOGGER.debug("Devices data structure: %s", devices_data)

                    # Extract devices from the total_list structure
                    all_devices = []
                    for device_group in devices_data:
                        _LOGGER.debug("Device group type: %s", device_group.get("type"))
                        if device_group.get("type") == "total_list":
                            devices = device_group.get("data", [])
                            _LOGGER.debug("Found %d devices in total_list", len(devices))
                            all_devices.extend(devices)

                    _LOGGER.info("Found %d devices", len(all_devices))
                    return all_devices
                else:
                    # Check for token expiration
                    error_msg = data.get("message", "")
                    if "token" in error_msg.lower() or "auth" in error_msg.lower():
                        _LOGGER.error("Token expired or invalid: %s", error_msg)
                        raise TokenExpiredError(error_msg)

                    _LOGGER.error("Failed to get devices: %s", error_msg)
                    return []
        except Exception as err:
            _LOGGER.error("Error getting devices: %s", err)
            return []

    async def send_device_command(
        self, device_id: str, signal: str, state: int
    ) -> bool:
        """Send command to device.

        Args:
            device_id: Device serial number
            signal: Signal name (e.g., 'rele1', 'rele-w')
            state: State to set (0 or 1)
        """
        if not self._token:
            _LOGGER.error("Not authenticated")
            return False

        session = await self._get_session()

        # Use apartment user_token if available, otherwise fallback to main token
        token_to_use = self._user_token if self._user_token else self._token

        try:
            url = f"{self._base_url}{API_SEND_SIGNAL}"
            params = {
                "serialnumber": device_id,
                "signal": signal,
                "state": str(state),
                "token": token_to_use,
                "app": API_APP_PARAM,
                "platform": API_PLATFORM_PARAM,
                "uniq_id": "",  # Empty in captured traffic
            }

            # Add area_guid if available
            if self._area_guid:
                params["area_guid"] = self._area_guid

            async with session.get(url, params=params) as response:
                data = await response.json()
                if data.get("error") == 0:
                    _LOGGER.info("Command sent successfully to device %s", device_id)
                    return True
                else:
                    error_msg = data.get("message", "")
                    # Check for token expiration
                    if "token" in error_msg.lower() or "auth" in error_msg.lower():
                        _LOGGER.error("Token expired or invalid: %s", error_msg)
                        raise TokenExpiredError(error_msg)

                    _LOGGER.error("Failed to send command: %s", error_msg)
                    return False
        except Exception as err:
            _LOGGER.error("Error sending device command: %s", err)
            return False

    def set_area_guid(self, area_guid: str) -> None:
        """Set area GUID for API requests."""
        self._area_guid = area_guid

    async def get_websocket_url(self) -> str | None:
        """Get WebSocket URL for real-time updates."""
        if not self._token:
            _LOGGER.error("Not authenticated")
            return None

        session = await self._get_session()

        # Use apartment user_token if available, otherwise fallback to main token
        token_to_use = self._user_token if self._user_token else self._token

        try:
            url = f"{self._base_url}{API_DEVICES_WSS}"
            params = {
                "token": token_to_use,
                "app": API_APP_PARAM,
                "platform": API_PLATFORM_PARAM,
            }

            if self._area_guid:
                params["area_guid"] = self._area_guid

            async with session.get(url, params=params) as response:
                data = await response.json()
                _LOGGER.debug("WebSocket API response: %s", data)

                if data.get("error") == 0:
                    wss_data = data.get("data", {})
                    _LOGGER.debug("WebSocket data structure: %s", wss_data)

                    # WebSocket URL is in 'wss' key as an array
                    wss_array = wss_data.get("wss", [])
                    if wss_array and len(wss_array) > 0:
                        wss_url = wss_array[0]
                        _LOGGER.info("Got WebSocket URL: %s", wss_url)
                        return wss_url
                    else:
                        _LOGGER.error("No WebSocket URL in response. Full data: %s", wss_data)
                        return None
                else:
                    error_msg = data.get("message", "")
                    _LOGGER.error("Failed to get WebSocket URL: %s", error_msg)
                    return None
        except Exception as err:
            _LOGGER.error("Error getting WebSocket URL: %s", err)
            return None

    async def close(self) -> None:
        """Close the API session."""
        if self._session:
            await self._session.close()
