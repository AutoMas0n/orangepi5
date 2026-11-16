"""Data coordinator for the local Tapo C200 integration."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    MOTOR_CALIBRATION_SECONDS,
    MOTOR_SETTLE_SECONDS,
)
from .device import (
    TapoAuthError,
    TapoC200Device,
    TapoCannotConnect,
    TapoError,
)

_LOGGER = logging.getLogger(__name__)


class TapoC200Coordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls the camera for the handful of values that change on their own."""

    config_entry: ConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, device: TapoC200Device
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {device.host}",
            update_interval=DEFAULT_UPDATE_INTERVAL,
        )
        self.config_entry = entry
        self.device = device
        # Filled in async_setup_entry before the first refresh.
        self.info: dict[str, Any] = {}
        self.capability: dict[str, Any] = {}

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.device.async_read_state()
        except TapoAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except TapoCannotConnect as err:
            raise UpdateFailed(f"cannot reach {self.device.host}: {err}") from err
        except TapoError as err:
            raise UpdateFailed(str(err)) from err

    # ── writes ────────────────────────────────────────────────────────────

    async def async_set_privacy(self, enabled: bool) -> None:
        await self._async_write_off_loop(self.device.async_call, "setPrivacyMode", enabled)

    async def async_set_led(self, enabled: bool) -> None:
        await self._async_write_off_loop(self.device.async_call, "setLEDEnabled", enabled)

    async def async_set_motion(self, enabled: bool) -> None:
        await self._async_write_off_loop(
            self.device.async_call, "setMotionDetection", enabled=enabled
        )

    async def _async_write_off_loop(self, call, func: str, *args, **kwargs) -> None:
        """Write, then re-read so entities show the camera's own answer.

        `async_refresh`, not `async_request_refresh`: the latter is debounced
        with a 10 s cooldown, so toggling a switch twice in a row (very easy in
        the UI) left the second change unconfirmed and the entity stale.
        """
        await call(func, *args, **kwargs)
        await self.async_refresh()

    async def async_nudge(self, dx: int, dy: int) -> None:
        """Move by a fixed number of degrees.

        Deliberately moveMotor(x, y) and not moveMotorStep(direction): the
        latter starts a continuous sweep that cannot be stopped (see const.py).
        """
        await self.device.async_call("moveMotor", dx, dy)
        self._schedule_position_refresh()

    async def async_calibrate(self) -> None:
        await self.device.async_call("calibrateMotor")
        # Calibration sweeps the full range and takes ~30 s.
        self._schedule_position_refresh(delay=MOTOR_CALIBRATION_SECONDS)

    async def async_goto_preset(self, preset_id: str) -> None:
        await self.device.async_call("setPreset", preset_id)
        self._schedule_position_refresh()

    async def async_save_preset(self, name: str) -> None:
        await self.device.async_call("savePreset", name)
        await self.async_refresh()

    async def async_delete_preset(self, preset_id: str) -> None:
        await self.device.async_call("deletePreset", preset_id)
        await self.async_refresh()

    def _schedule_position_refresh(self, delay: float = MOTOR_SETTLE_SECONDS) -> None:
        """Re-read the position once the motor has finished moving.

        A step is not instantaneous (measured: ~2 s to travel and report), so
        refreshing immediately would read the *old* angle and leave the sensor
        showing where the camera used to point. This deliberately does not
        block the service call - a PTZ button should return immediately.
        """
        self.hass.async_create_task(self._async_refresh_position(delay))

    async def _async_refresh_position(self, delay: float) -> None:
        await asyncio.sleep(delay)
        try:
            await self.async_refresh()
        except Exception as err:  # noqa: BLE001 - a stale angle is not fatal
            _LOGGER.debug("position refresh failed: %s", err)

