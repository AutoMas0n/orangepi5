"""The local Tapo C200 integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_USERNAME,
    Platform,
)
from homeassistant.core import HomeAssistant

from .const import CONF_RTSP_PASSWORD, CONF_RTSP_USERNAME, DOMAIN
from .coordinator import TapoC200Coordinator
from .device import TapoC200Device, TapoError

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CAMERA,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

type TapoC200ConfigEntry = ConfigEntry[TapoC200Coordinator]


async def async_setup_entry(hass: HomeAssistant, entry: TapoC200ConfigEntry) -> bool:
    """Set up one camera."""
    device = TapoC200Device(
        entry.data[CONF_HOST],
        entry.data.get(CONF_USERNAME, "admin"),
        entry.data[CONF_PASSWORD],
        rtsp_username=entry.data.get(CONF_RTSP_USERNAME),
        rtsp_password=entry.data.get(CONF_RTSP_PASSWORD),
    )
    coordinator = TapoC200Coordinator(hass, entry, device)

    # Reads that only happen once. Failure here is fatal: an entity-less device
    # is worse than an explicit config-entry error.
    coordinator.info = await device.async_read_info()

    # PTZ capability is optional: pytapo's getMotorCapability asks for
    # `motor.capability`, which this firmware does not have (it answers
    # -40101). The raw `ptz.capability` request works, but a camera that
    # refuses even that should still get its non-PTZ entities.
    try:
        coordinator.capability = await device.async_motor_capability()
    except TapoError as err:
        _LOGGER.warning(
            "%s: PTZ capability unknown (%s); PTZ entities may be incomplete",
            entry.data[CONF_HOST],
            err,
        )
        coordinator.capability = {}

    # Probe once for a readable pan/tilt angle. Firmware 1.4.6 answers
    # getPtzStatus with an empty result instead of an error, so this cannot be
    # inferred from capability - it has to be looked at.
    device.position_readable = coordinator.position_readable = bool(
        await device.async_motor_status()
    )
    if not coordinator.position_readable:
        _LOGGER.info(
            "%s: camera does not report a pan/tilt angle (firmware removed the "
            "read); PTZ buttons still work, position sensors are not created",
            entry.data[CONF_HOST],
        )

    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: TapoC200ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
