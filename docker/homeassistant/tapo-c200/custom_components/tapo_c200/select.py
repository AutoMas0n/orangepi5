"""Select platform: jump to a saved camera preset."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import ERROR_PRESET_NOT_FOUND
from .coordinator import TapoC200Coordinator
from .device import TapoError
from .entity import TapoC200Entity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator: TapoC200Coordinator = entry.runtime_data
    async_add_entities([TapoPresetSelect(coordinator)])


class TapoPresetSelect(TapoC200Entity, SelectEntity):
    """Saved positions.

    The camera reports presets as {"<id>": "<name>"}; this entity shows names
    as the options and remembers which one was selected, because the camera
    itself only reports the current *position*, not the preset it came from.
    """

    _attr_translation_key = "preset"
    _attr_icon = "mdi:map-marker-radius"

    def __init__(self, coordinator: TapoC200Coordinator) -> None:
        super().__init__(coordinator, "preset")
        self._current: str | None = None

    def _presets(self) -> dict[str, str]:
        return (self.coordinator.data or {}).get("presets") or {}

    @property
    def options(self) -> list[str]:
        return list(self._presets().values())

    @property
    def current_option(self) -> str | None:
        presets = self._presets()
        if self._current in presets.values():
            return self._current
        return None

    async def async_select_option(self, option: str) -> None:
        preset_id = next(
            (pid for pid, name in self._presets().items() if name == option), None
        )
        if preset_id is None:
            raise HomeAssistantError(
                translation_domain="tapo_c200",
                translation_key="preset_missing",
                translation_placeholders={"name": option},
            )
        try:
            await self.coordinator.async_goto_preset(preset_id)
        except TapoError as err:
            if str(ERROR_PRESET_NOT_FOUND) in str(err):
                raise HomeAssistantError(
                    translation_domain="tapo_c200",
                    translation_key="preset_missing",
                    translation_placeholders={"name": option},
                ) from err
            raise
        self._current = option
        self.async_write_ha_state()
