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
    entities: list[SensorEntity] = [
        TapoAngleSensor(coordinator, "pan", "mdi:rotate-right"),
        TapoAngleSensor(coordinator, "tilt", "mdi:angle-acute"),
    ]
    if coordinator.info.get("sd"):
        entities.append(TapoStorageSensor(coordinator))
    async_add_entities(entities)


class TapoAngleSensor(TapoC200Entity, SensorEntity):
    """Pan or tilt angle, in degrees.

    Read from `ptz.status` (angle_x / angle_y) in the coordinator poll. This is
    a CoordinatorEntity, so `async_update` is never called - values have to
    come from `coordinator.data`.

    `angle_x` wraps at 360 while `angle_y` is signed, which is how the camera
    reports them - the values are passed through unchanged rather than
    normalised, so automations can compare against what pytapo returns.
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
