# Tapo C200 in Home Assistant (fully local)

A small custom integration that talks to a TP-Link Tapo C200 over the LAN only.
The camera is set up **without a TP-Link cloud account** (see
`github.com/JurajNyiri/pytapo` and the cloudless provisioning notes in the
sibling `tapo-local-setup` repo), and this integration never contacts TP-Link.

    custom_components/tapo_c200/     the integration (this repo is the source of truth)
    docker/homeassistant/README.md   how to install / where it runs

Live state on the Orange Pi: entry `Tapo_Camera`, camera at `192.168.2.57`
(pinned by a Pi-hole static lease), 15 entities, PTZ verified end to end.

## What you get

| Entity | What it does |
| --- | --- |
| `camera.tapo_camera_main_stream` | RTSP stream1 - H.264 1920x1080 @ 15 fps |
| `camera.tapo_camera_sub_stream` | RTSP stream2 - H.264 1280x720 @ 15 fps |
| `button.tapo_camera_ptz_up/down/left/right` | one-step pan/tilt nudge |
| `button.tapo_camera_calibrate_motor` | full motor recalibration (~35 s) |
| `select.tapo_camera_preset` | jump to a saved position |
| `sensor.tapo_camera_pan_angle` / `tilt_angle` | current position in degrees |
| `sensor.tapo_camera_sd_card_used` | SD card fill level (None when no card) |
| `switch.tapo_camera_privacy_mode` | lens mask on/off |
| `switch.tapo_camera_motion_detection` | motion detection on/off |
| `switch.tapo_camera_status_led` | front LED on/off |
| `binary_sensor.tapo_camera_motion_detection_active` | mirrors the switch (see caveat) |

## Install

The integration is service state in the HA config, but the source lives here:

    scp -r docker/homeassistant/tapo-c200/custom_components/tapo_c200 \
        orangepi@192.168.2.113:/home/orangepi/docker-data/homeassistant/custom_components/
    docker restart homeassistant

Home Assistant caches the custom-component list at startup, so a **restart is
required** before the flow is visible. `pytapo` is not installed in the
container by default; the manifest pins `pytapo==3.4.31` and HA installs it on
first setup (verified: it does, and it stays across restarts).

Then add it in the UI (Settings -> Devices & services -> Add integration ->
"Tapo C200 (local)"):

1. **Host** `192.168.2.57`, **username** `admin`, **password** = the camera
   account password (the one an admin login uses).
2. Second step: **RTSP username** `tapoadmin`, **RTSP password** = the same
   password. This is the "third account" created during cloudless
   provisioning; RTSP/ONVIF uses it, *not* `admin`. Leaving it blank makes the
   live feed fail with `401 Unauthorized`.

Deleting and re-adding the entry is the way to change credentials (the flow
does not expose options).

### Static lease

`a8:29:dc:ab:b5:50 -> 192.168.2.57` is pinned through Pi-hole's DHCP
(`static-lease` script in the `pihole-local-dns` repo), so the host in the
config entry stays correct.

## PTZ: what the API actually is on this firmware

Verified against C200 **hw 5.0, fw 1.2.1 Build 250324**. This is the part
pytapo does not document, and it is why the stock `Tapo.getMotorCapability()`
fails here.

* Reads live under the **`ptz`** namespace, movement commands under **`motor`**.
  `Tapo.getMotorCapability()` requests `motor.capability` and gets `-40101`;
  the raw request that works is
  `{"method":"get","ptz":{"name":["capability"]}}`.
* Position: `{"method":"get","ptz":{"name":["status"]}}` ->
  `angle_x` (0-360, wraps), `angle_y` (signed, roughly -15..55 on this unit).
* `moveMotorStep(direction)` takes a **direction selector**, not degrees of
  travel. Measured by reading `angle_x`/`angle_y` around each call:

  | value | effect |
  | --- | --- |
  | 90 | `angle_y` increases - looks **up** |
  | 270 | `angle_y` decreases - looks **down** |
  | 0 | `angle_x` increases - pans clockwise from above |
  | 180 | `angle_x` decreases - opposite |

* At the end of travel the camera answers **-64304** "Maximum Pan/Tilt range
  reached (MOTOR_LOCKED_ROTOR)". That is normal, not a fault: the button
  surfaces a translatable "already at the end of its travel" error instead of a
  raw exception. **-64303** is motor busy, **-64302** preset not found.
* Presets are their own namespace: get via
  `{"preset":{"name":["preset"]}}`, save via
  `{"preset":{"set_preset":{"name":..., "save_ptz":"1"}}}`, delete via
  `{"preset":{"remove_preset":{"id":[...]}}}`. Max 8 presets.
* A step takes ~2 s to physically move and report, so the integration re-reads
  the position after a delay instead of immediately (see below).

## Design notes / traps hit while building this

* **pytapo's constructor logs in.** `Tapo(...)` calls `getBasicInfo()` inside
  `__init__`, and pytapo's `AsyncHandler` creates its own event loop and calls
  `run_until_complete`. Constructing it on HA's event-loop thread raises
  `RuntimeError: Cannot run the event loop while another loop is running`.
  `device.py` therefore creates the client **inside the executor**.
* **No `async_update` on `CoordinatorEntity`.** The angle sensors originally
  polled the position in `async_update`, which HA never calls for coordinator
  entities, so they sat at `unknown`. Position is now part of the 60 s poll.
* **`async_request_refresh()` is debounced** (10 s). Two quick switch presses
  left the second state unconfirmed. Writes now call `async_refresh()`.
* **`camera_proxy` returns 500 unless `use_stream_for_stills` is True.** With
  `async_camera_image` returning `None` and that flag left at its default, HA
  raises "Unable to get image" and every dashboard tile 500s even though the
  stream is fine. `camera.py` sets it True and lets HA grab stills from RTSP.
* **`getSDCard()` returns a list of one-key wrappers** (`[{"hd_info_1": {...}}]`).
  `device.async_sd_card()` flattens the first slot; a camera with no card
  reports `status: "offline"` and the sensor reads `None` rather than `0 %`.
* **Unsupported on this firmware:** `getAlarmConfig` (-40210),
  `getEvents`/`searchDetectionList` (-71114), `getSirenStatus`. That is why the
  motion entity reports the *setting*, not live motion - real motion triggers
  need ONVIF events or the camera's own recordings.

## Verify

    # entities exist
    curl -s -H "Authorization: Bearer <token>" http://192.168.2.113:8123/api/states \
      | jq -r '.[].entity_id' | grep tapo

    # a still (should be a JPEG, with the camera's own OSD timestamp burnt in)
    curl -s -H "Authorization: Bearer <token>" \
      http://192.168.2.113:8123/api/camera_proxy/camera.tapo_camera_sub_stream -o /tmp/tapo.jpg

The OSD clock in the image is the quickest proof the frame is live.

## Caveat: check pytapo first

Before adding another C200 (or any Tapo model), check the pytapo repo for the
current state of things - namespace splits, error codes and the login scheme
(`klap` / `tpap` / legacy `pytapo`) change between firmware builds. See the
`tapo-c200-local-setup` skill for the full procedure.
