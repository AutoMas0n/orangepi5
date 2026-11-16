"""Buttons: PTZ directions plus maintenance actions."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.button import (
    ButtonDeviceClass,
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import ERROR_MOTOR_BUSY, ERROR_MOTOR_LOCKED, PTZ_DIRECTIONS
from .coordinator import TapoC200Coordinator
from .device import TapoError
from .entity import TapoC200Entity


@dataclass(frozen=True, kw_only=True)
class TapoPtzButtonDescription(ButtonEntityDescription):
    """A PTZ nudge button."""

    dx: int
    dy: int


PTZ_BUTTONS: tuple[TapoPtzButtonDescription, ...] = tuple(
    TapoPtzButtonDescription(
        key=f"ptz_{name}", translation_key=f"ptz_{name}", icon=icon,
        dx=PTZ_DIRECTIONS[direction][0], dy=PTZ_DIRECTIONS[direction][1],
    )
    for name, direction, icon in (
        ("up", "up", "mdi:arrow-up-bold"),
        ("down", "down", "mdi:arrow-down-bold"),
        ("left", "counter_clockwise", "mdi:arrow-left-bold"),
        ("right", "clockwise", "mdi:arrow-right-bold"),
    )
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator: TapoC200Coordinator = entry.runtime_data
    entities: list[ButtonEntity] = [
        TapoPtzButton(coordinator, description) for description in PTZ_BUTTONS
    ]
    entities.append(TapoCalibrateButton(coordinator))
    async_add_entities(entities)


class TapoPtzButton(TapoC200Entity, ButtonEntity):
    """Nudge the camera by a fixed number of degrees."""

    entity_description: TapoPtzButtonDescription

    def __init__(
        self, coordinator: TapoC200Coordinator, description: TapoPtzButtonDescription
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    async def async_press(self) -> None:
        try:
            await self.coordinator.async_nudge(
                self.entity_description.dx, self.entity_description.dy
            )
        except TapoError as err:
            message = str(err)
            # Reaching a limit is not a fault: the camera is simply already at
            # the end of its travel, which happens constantly with a 4-way
            # nudge button. Report it as handled, not as an error.
            if str(ERROR_MOTOR_LOCKED) in message:
                raise HomeAssistantError(
                    translation_domain="tapo_c200",
                    translation_key="motor_at_limit",
                ) from err
            if str(ERROR_MOTOR_BUSY) in message:
                raise HomeAssistantError(
                    translation_domain="tapo_c200",
                    translation_key="motor_busy",
                ) from err
            raise


class TapoCalibrateButton(TapoC200Entity, ButtonEntity):
    """Re-run the motor calibration (takes several seconds)."""

    _attr_translation_key = "calibrate"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_device_class = ButtonDeviceClass.RESTART

    def __init__(self, coordinator: TapoC200Coordinator) -> None:
        super().__init__(coordinator, "calibrate")

    async def async_press(self) -> None:
        await self.coordinator.async_calibrate()
