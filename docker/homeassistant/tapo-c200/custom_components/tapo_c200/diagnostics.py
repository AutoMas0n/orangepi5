"""Diagnostics: redacted dump for bug reports."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from .coordinator import TapoC200Coordinator

REDACT = {"password", "rtsp_password", "username", "rtsp_username", "stok"}


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            k: ("**REDACTED**" if k.lower() in REDACT else _redact(v))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_redact(v) for v in value]
    return value


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry
) -> dict[str, Any]:
    coordinator: TapoC200Coordinator = entry.runtime_data
    return {
        "entry": {
            "host": entry.data.get("host"),
            "unique_id": entry.unique_id,
        },
        "basic_info": _redact(coordinator.info.get("basic", {})),
        "ptz_capability": _redact(coordinator.capability),
        "state": _redact(coordinator.data or {}),
    }
