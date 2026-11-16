"""Config flow for the local Tapo C200 integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers import config_validation as cv

from .const import CONF_RTSP_PASSWORD, CONF_RTSP_USERNAME, DEFAULT_USERNAME, DOMAIN
from .device import (
    TapoAuthError,
    TapoC200Device,
    TapoCannotConnect,
    TapoError,
)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_USERNAME, default=DEFAULT_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
    }
)

STEP_RTSP_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_RTSP_USERNAME): cv.string,
        vol.Optional(CONF_RTSP_PASSWORD): cv.string,
    }
)


async def _async_try_login(data: dict[str, Any]) -> dict[str, Any]:
    """Prove host+credentials work, returning basic_info.

    Note there is no cloud fallback here by design: this integration only ever
    talks to the camera on the LAN.
    """
    device = TapoC200Device(
        data[CONF_HOST],
        data.get(CONF_USERNAME, DEFAULT_USERNAME),
        data[CONF_PASSWORD],
        rtsp_username=data.get(CONF_RTSP_USERNAME),
        rtsp_password=data.get(CONF_RTSP_PASSWORD),
    )
    return await device.async_validate()


class TapoC200ConfigFlow(ConfigFlow, domain=DOMAIN):
    """User-driven setup; no discovery, since the camera is never cloud-visible."""

    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._basic: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                basic = await _async_try_login(user_input)
            except TapoCannotConnect:
                errors["base"] = "cannot_connect"
            except TapoAuthError:
                errors["base"] = "invalid_auth"
            except TapoError:
                errors["base"] = "unknown"
            else:
                mac = (basic.get("mac") or "").lower().replace("-", ":")
                if mac:
                    await self.async_set_unique_id(mac)
                    self._abort_if_unique_id_configured(
                        updates={CONF_HOST: user_input[CONF_HOST]}
                    )
                self._data = dict(user_input)
                self._basic = basic
                return await self.async_step_rtsp()

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_rtsp(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Optional separate RTSP account, then finish."""
        if user_input is not None:
            data = dict(self._data)
            if user_input.get(CONF_RTSP_USERNAME):
                data[CONF_RTSP_USERNAME] = user_input[CONF_RTSP_USERNAME]
            if user_input.get(CONF_RTSP_PASSWORD):
                data[CONF_RTSP_PASSWORD] = user_input[CONF_RTSP_PASSWORD]
            name = (
                self._basic.get("device_alias") or self._basic.get("device_name") or "Tapo"
            )
            return self.async_create_entry(title=name, data=data)

        return self.async_show_form(step_id="rtsp", data_schema=STEP_RTSP_DATA_SCHEMA)

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        if user_input is not None and entry is not None:
            data = {**entry.data, **user_input}
            try:
                await _async_try_login(data)
            except TapoCannotConnect:
                errors["base"] = "cannot_connect"
            except TapoAuthError:
                errors["base"] = "invalid_auth"
            except TapoError:
                errors["base"] = "unknown"
            else:
                self.hass.config_entries.async_update_entry(entry, data=data)
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_USERNAME,
                        default=(entry.data.get(CONF_USERNAME) if entry else None),
                    ): cv.string,
                    vol.Required(CONF_PASSWORD): cv.string,
                }
            ),
            errors=errors,
        )
