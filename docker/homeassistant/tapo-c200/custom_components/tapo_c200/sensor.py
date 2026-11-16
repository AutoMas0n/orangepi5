"""Sensors: pan/tilt position and storage."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import TapoC200Coordinator
from .entity import TapoC200Entity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator: TapoC200Coordinator = entry.runtime_data
    entities: list[SensorEntity] = []
    # Only offer a position sensor if the camera will report one. Firmware 1.4.6
    # dropped the read entirely, and an always-`unknown` sensor is worse than
    # no sensor at all - it looks broken rather than unsupported.
    if coordinator.position_readable:
        entities += [
            TapoAngleSensor(coordinator, "pan", "mdi:rotate-right"),
            TapoAngleSensor(coordinator, "tilt", "mdi:angle-acute"),
        ]
    if coordinator.info.get("sd"):
        entities.append(TapoStorageSensor(coordinator))
    async_add_entities(entities)


class TapoAngleSensor(TapoC200Entity, SensorEntity):
    """Pan or tilt angle, in degrees.

    Read from the `ptz.status` read (angle_x / angle_y) in the coordinator poll.
    This is a CoordinatorEntity, so `async_update` is never called - values
    have to come from `coordinator.data`.

    `angle_x` wraps at 360 while `angle_y` is signed, which is how the camera
    reports them - the values are passed through unchanged rather than
    normalised, so automations can compare against what pytapo returns.

    BEWARE: firmware 1.4.6 (Build 260709) REMOVED that read. `getPtzStatus`
    still exists but answers an empty result, so this sensor is permanently
    `unknown` there. It is registered only when the position is readable, which
    `async_setup_entry` decides by probing once - see `TapoC200Device
    .async_motor_status`. A sensor that never reports is worse than no sensor.
    """

    _attr_native_unit_of_measurement = "°"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self, coordinator: TapoC200Coordinator, axis: str, icon: str
    ) -> None:
        super().__init__(coordinator, f"angle_{axis}")
        self._axis = axis
        self._attr_icon = icon
        self._attr_translation_key = f"angle_{axis}"

    @property
    def native_value(self) -> float | None:
        status = (self.coordinator.data or {}).get("motor") or {}
        key = "angle_x" if self._axis == "pan" else "angle_y"
        try:
            return round(float(status[key]), 1)
        except (KeyError, TypeError, ValueError):
            return None


class TapoStorageSensor(TapoC200Entity, SensorEntity):
    """SD card fill level.

    device.async_sd_card() flattens the camera's list-of-slots wrapper. A
    camera with no card reports status "offline", in which case the sensor
    reads None rather than 0 % - "no card" and "empty card" must not look the
    same.
    """

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_translation_key = "storage"
    _attr_icon = "mdi:micro-sd"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: TapoC200Coordinator) -> None:
        super().__init__(coordinator, "storage")

    @property
    def native_value(self) -> float | None:
        sd = self.coordinator.info.get("sd") or {}
        if not isinstance(sd, dict) or sd.get("status") != "online":
            return None
        try:
            return float(sd.get("percent", 0))
        except (TypeError, ValueError):
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        sd = self.coordinator.info.get("sd") or {}
        if not isinstance(sd, dict):
            return {}
        return {
            "status": sd.get("status"),
            "total_space": sd.get("total_space"),
            "free_space": sd.get("free_space"),
            "write_protect": sd.get("write_protect"),
        }
