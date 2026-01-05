"""Config flow for Ujin Smart Home integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .api import UjinApiClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): cv.string,
    }
)

STEP_CODE_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("code"): cv.string,
    }
)


class UjinConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Ujin Smart Home."""

    VERSION = 1

    def __init__(self):
        """Initialize config flow."""
        self._email: str | None = None
        self._api_client: UjinApiClient | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - email input."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                self._email = user_input[CONF_EMAIL]
                self._api_client = UjinApiClient(email=self._email, session=None)

                # Send authentication code
                result = await self._api_client.send_auth_code()

                if result.get("error") == 0:
                    _LOGGER.info("Auth code sent to %s", self._email)
                    # Move to code verification step
                    return await self.async_step_code()
                else:
                    errors["base"] = "cannot_send_code"
                    _LOGGER.error("Failed to send auth code: %s", result.get("message"))
            except Exception as err:
                _LOGGER.error("Failed to send auth code: %s", err)
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "info": "Введите email для получения кода подтверждения"
            },
        )

    async def async_step_code(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle code verification step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                code = user_input["code"]

                # Verify the code
                if await self._api_client.verify_auth_code(code):
                    # Save token and email for future use
                    token = self._api_client._token
                    user_token = self._api_client._user_token

                    # Try to get area_guid by fetching devices once
                    # This also validates the token
                    devices = await self._api_client.get_devices()
                    area_guid = self._api_client._area_guid

                    _LOGGER.info(
                        "Authentication successful. Token: %s..., user_token: %s..., area_guid: %s",
                        token[:20] if token else "None",
                        user_token[:20] if user_token else "None",
                        area_guid
                    )

                    # Create entry with token, user_token and area_guid
                    return self.async_create_entry(
                        title=f"Ujin ({self._email})",
                        data={
                            CONF_EMAIL: self._email,
                            "token": token,
                            "user_token": user_token,
                            "area_guid": area_guid,
                        },
                    )
                else:
                    errors["base"] = "invalid_code"
            except Exception as err:
                _LOGGER.error("Failed to verify code: %s", err)
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="code",
            data_schema=STEP_CODE_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "info": f"Введите код из письма на {self._email}"
            },
        )
