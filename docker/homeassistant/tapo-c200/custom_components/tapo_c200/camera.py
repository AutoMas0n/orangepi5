"""Camera platform: main and sub RTSP streams."""

from __future__ import annotations

from homeassistant.components.camera import Camera, CameraEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import TapoC200Coordinator
from .entity import TapoC200Entity

STREAMS = (("stream1", "main_stream"), ("stream2", "sub_stream"))


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator: TapoC200Coordinator = entry.runtime_data
    async_add_entities(
        TapoC200Camera(coordinator, stream, name) for stream, name in STREAMS
    )


class TapoC200Camera(TapoC200Entity, Camera):
    """One RTSP stream of the camera.

    Both streams are exposed because the camera encodes them independently:
    stream1 is 1920x1080 and stream2 is 1280x720 (verified with ffprobe). The
    sub stream is the one to use for dashboards that keep many tiles on screen.
    """

    _attr_supported_features = CameraEntityFeature.STREAM

    def __init__(
        self, coordinator: TapoC200Coordinator, stream: str, translation_key: str
    ) -> None:
        TapoC200Entity.__init__(self, coordinator, f"camera_{stream}")
        Camera.__init__(self)
        self._stream = stream
        self._attr_translation_key = translation_key

    @property
    def use_stream_for_stills(self) -> bool:
        """Take snapshots from the RTSP stream.

        Required: `async_camera_image` returns None, so without this Home
        Assistant raises "Unable to get image" and every camera_proxy request
        answers 500 - which is how the dashboard tile ends up blank even
        though the stream itself is fine.
        """
        return True

    async def stream_source(self) -> str | None:
        return self.coordinator.device.rtsp_url(self._stream)

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        # HA takes stills from the stream via ffmpeg; the camera's own snapshot
        # endpoint is not exposed by pytapo and would be a second auth path.
        return None
