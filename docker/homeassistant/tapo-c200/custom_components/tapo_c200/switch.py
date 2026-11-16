"""Switches: privacy mode, status LED, motion detection."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
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
    async_add_entities(
        [
            TapoPrivacySwitch(coordinator),
            TapoDetectionSwitch(coordinator),
            TapoLedSwitch(coordinator),
        ]
    )


def _on_off(value: object) -> bool:
    """pytapo reports these as the strings 'on'/'off'."""
    return str(value).lower() == "on"


class TapoPrivacySwitch(TapoC200Entity, SwitchEntity):
    """Lens mask.

    When on, the camera serves a masked image instead of the real scene. The
    RTSP stream keeps running, so a dashboard tile shows the mask rather than
    going unavailable - which is the point: you can see it is deliberate.
    """

    _attr_translation_key = "privacy_mode"
    _attr_icon = "mdi:eye-off"

    def __init__(self, coordinator: TapoC200Coordinator) -> None:
        super().__init__(coordinator, "privacy_mode")

    @property
    def is_on(self) -> bool:
        return _on_off((self.coordinator.data or {}).get("privacy", {}).get("enabled"))

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_set_privacy(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_set_privacy(False)


class TapoDetectionSwitch(TapoC200Entity, SwitchEntity):
    """Motion detection, i.e. whether the camera raises motion events."""

    _attr_translation_key = "motion_detection"
    _attr_icon = "mdi:motion-sensor"

    def __init__(self, coordinator: TapoC200Coordinator) -> None:
        super().__init__(coordinator, "motion_detection")

    @property
    def is_on(self) -> bool:
        return _on_off((self.coordinator.data or {}).get("motion", {}).get("enabled"))

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_set_motion(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_set_motion(False)


class TapoLedSwitch(TapoC200Entity, SwitchEntity):
    """The status LED on the front of the camera."""

    _attr_translation_key = "status_led"
    _attr_icon = "mdi:led-on"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: TapoC200Coordinator) -> None:
        super().__init__(coordinator, "status_led")

    @property
    def is_on(self) -> bool:
        return _on_off((self.coordinator.data or {}).get("led", {}).get("enabled"))

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_set_led(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_set_led(False)
