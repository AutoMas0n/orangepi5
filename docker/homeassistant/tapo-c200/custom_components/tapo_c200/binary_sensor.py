"""Binary sensor: motion detection state.

The C200 does not expose a push motion event over the local API in a way
pytapo surfaces, so this reports the camera's motion-detection *setting*
rather than transient motion. Kept as a binary_sensor so it groups with the
switch semantically and can be used as an automation condition.

If you need actual motion triggers, point the camera's own detection at an
ONVIF event source or watch recordings; polling `getEvents` on this firmware
fails with -71114 (searchDetectionList unsupported).
"""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
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
    async_add_entities([TapoMotionSensor(coordinator)])


class TapoMotionSensor(TapoC200Entity, BinarySensorEntity):
    """True while motion detection is enabled on the camera."""

    _attr_device_class = BinarySensorDeviceClass.MOTION
    _attr_translation_key = "motion_detection_active"

    def __init__(self, coordinator: TapoC200Coordinator) -> None:
        super().__init__(coordinator, "motion_active")

    @property
    def is_on(self) -> bool:
        state = (self.coordinator.data or {}).get("motion", {})
        return str(state.get("enabled")).lower() == "on"
