"""Base entity for the local Tapo C200 integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import TapoC200Coordinator


class TapoC200Entity(CoordinatorEntity[TapoC200Coordinator]):
    """Entity belonging to one camera."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: TapoC200Coordinator, unique_key: str) -> None:
        super().__init__(coordinator)
        device = coordinator.device
        basic = coordinator.info.get("basic", {})
        mac = basic.get("mac", "").lower().replace("-", ":")
        # The MAC is the stable identity: DHCP reservations and IP changes must
        # not create a second device in the registry.
        self._attr_unique_id = f"{mac or device.host}_{unique_key}"
        info = DeviceInfo(
            identifiers={(DOMAIN, mac or device.host)},
            name=basic.get("device_alias") or "Tapo C200",
            manufacturer="TP-Link",
            model=basic.get("device_name") or basic.get("device_model"),
            sw_version=basic.get("sw_version"),
            hw_version=basic.get("hw_version"),
            serial_number=basic.get("mac"),
            configuration_url=f"http://{device.host}",
        )
        if mac:
            info["connections"] = {(CONNECTION_NETWORK_MAC, mac)}
        self._attr_device_info = info

    @property
    def available(self) -> bool:
        return super().available
