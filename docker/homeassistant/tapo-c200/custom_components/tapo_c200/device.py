"""Thin async wrapper around the blocking pytapo library.

pytapo is fully synchronous (requests + socket), so every call runs in an
executor. A single Tapo instance is shared and serialised behind a lock: the
camera drops requests that arrive while it is busy with a PTZ move, and its
`start_seq` counter is not safe to share across concurrent requests.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from pytapo import Tapo

_LOGGER = logging.getLogger(__name__)


class TapoAuthError(Exception):
    """The camera rejected the credentials."""


class TapoCannotConnect(Exception):
    """The camera is unreachable."""


class TapoError(Exception):
    """The camera answered with an error."""


class TapoC200Device:
    """Serialised access to one camera."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        *,
        rtsp_username: str | None = None,
        rtsp_password: str | None = None,
    ) -> None:
        self.host = host
        self.username = username
        self._password = password
        self.rtsp_username = rtsp_username or username
        self.rtsp_password = rtsp_password if rtsp_password is not None else password
        self._lock = asyncio.Lock()
        self._tapo: Tapo | None = None

    # ── plumbing ──────────────────────────────────────────────────────────

    def _connect(self) -> Tapo:
        """Create the client.

        NOT cheap: pytapo's constructor logs in immediately (__init__ calls
        getBasicInfo), and pytapo's AsyncHandler creates its own event loop and
        calls run_until_complete on it. Called from the event-loop thread that
        raises "Cannot run the event loop while another loop is running", so
        this must only ever be reached from inside the executor.
        """
        if self._tapo is None:
            self._tapo = Tapo(self.host, self.username, self._password)
        return self._tapo

    async def _async_tapo(self) -> Tapo:
        """Get the client, building it inside the executor if needed."""
        if self._tapo is not None:
            return self._tapo
        return await asyncio.get_running_loop().run_in_executor(None, self._connect)

    async def async_call(self, func: str, *args: Any, **kwargs: Any) -> Any:
        """Run `tapo.<func>(...)` in an executor, one call at a time."""
        async with self._lock:
            tapo = await self._async_tapo()
            target = getattr(tapo, func, None)
            if target is None:
                raise TapoError(f"{func} is not supported by pytapo")
            try:
                return await asyncio.get_running_loop().run_in_executor(
                    None, lambda: target(*args, **kwargs)
                )
            except Exception as err:  # noqa: BLE001 - pytapo raises bare Exception
                message = str(err)
                # pytapo signals these with plain Exception and a text prefix.
                if "-40209" in message or "Invalid authentication" in message:
                    raise TapoAuthError(message) from err
                if "Connection" in message or "timed out" in message:
                    raise TapoCannotConnect(message) from err
                raise TapoError(message) from err

    async def async_validate(self) -> dict[str, Any]:
        """Log in and return basic_info, proving host+credentials work."""
        info = await self.async_call("getBasicInfo")
        basic = (info or {}).get("device_info", {}).get("basic_info", {})
        if not basic:
            raise TapoError("camera returned no basic_info")
        return basic

    # ── reads used by the coordinator ─────────────────────────────────────

    async def async_read_state(self) -> dict[str, Any]:
        """One poll's worth of state.

        Deliberately small: every call is a ~170 ms round trip and the camera
        starves its video encoder when hammered, so polling reads only what an
        entity actually displays. Settings that only change when we write them
        are read once at setup instead.
        """
        state: dict[str, Any] = {}
        state["privacy"] = await self.async_call("getPrivacyMode")
        state["motion"] = await self.async_call("getMotionDetection")
        state["presets"] = await self.async_call("getPresets")
        state["led"] = await self.async_call("getLED")
        # ~170 ms extra on a 60 s poll. Worth it: pan/tilt position is the one
        # value that changes without us writing it (preset jumps, the phone
        # app, the camera's own patrol), so it has to come from the poll.
        try:
            state["motor"] = await self.async_motor_status()
        except TapoError as err:
            _LOGGER.debug("%s: motor status unavailable: %s", self.host, err)
            state["motor"] = {}
        return state

    async def async_read_info(self) -> dict[str, Any]:
        """Static device info, read once at setup."""
        info: dict[str, Any] = {}
        info["basic"] = await self.async_validate()
        for key, func in (
            ("time", "getTime"),
            ("record_plan", "getRecordPlan"),
        ):
            try:
                info[key] = await self.async_call(func)
            except TapoError as err:
                _LOGGER.debug("%s: %s unavailable: %s", self.host, func, err)
                info[key] = None
        info["sd"] = await self.async_sd_card()
        return info

    async def async_sd_card(self) -> dict[str, Any]:
        """First SD card slot, flattened.

        pytapo returns `[{"hd_info_1": {...}}]` - a list of one-key wrappers, one
        entry per slot. Cameras without a card still report a slot with
        status/detect_status "offline" and all sizes "0B".
        """
        try:
            raw = await self.async_call("getSDCard")
        except TapoError as err:
            _LOGGER.debug("%s: getSDCard unavailable: %s", self.host, err)
            return {}
        if isinstance(raw, list):
            for entry in raw:
                if isinstance(entry, dict) and entry:
                    first = next(iter(entry.values()))
                    if isinstance(first, dict):
                        return first
            return {}
        return raw if isinstance(raw, dict) else {}

    async def async_motor_status(self) -> dict[str, Any]:
        """Pan/tilt position. Uses the `ptz` namespace, not `motor`.

        On C200 5.0 firmware the capability/status reads live under `ptz` while
        the movement *commands* live under `motor`. pytapo's getMotorCapability
        asks for `motor.capability` and fails with -40101 on this camera; this
        raw request is the one that works.
        """
        async with self._lock:
            tapo = await self._async_tapo()
            try:
                result = await asyncio.get_running_loop().run_in_executor(
                    None,
                    lambda: tapo.performRequest(
                        {"method": "get", "ptz": {"name": ["status"]}}
                    ),
                )
            except Exception as err:  # noqa: BLE001
                raise TapoError(str(err)) from err
        return (result or {}).get("ptz", {}).get("status", {})

    async def async_motor_capability(self) -> dict[str, Any]:
        """PTZ capability flags (preset_supported, tour_supported, ...)."""
        async with self._lock:
            tapo = await self._async_tapo()
            try:
                result = await asyncio.get_running_loop().run_in_executor(
                    None,
                    lambda: tapo.performRequest(
                        {"method": "get", "ptz": {"name": ["capability"]}}
                    ),
                )
            except Exception as err:  # noqa: BLE001
                raise TapoError(str(err)) from err
        return (result or {}).get("ptz", {}).get("capability", {})

    # ── RTSP ──────────────────────────────────────────────────────────────

    def rtsp_url(self, stream: str = "stream1") -> str:
        """RTSP URL for HA's stream component.

        NOTE: unlike the iCSee cameras on this LAN, the Tapo parses its RTSP
        path normally and expects real percent-encoding, so the credentials are
        quoted with urlencode here (verified with ffprobe on both streams).
        """
        from urllib.parse import quote

        user = quote(self.rtsp_username, safe="")
        password = quote(self.rtsp_password, safe="")
        return f"rtsp://{user}:{password}@{self.host}:554/{stream}"
