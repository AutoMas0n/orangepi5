# Home Assistant

Container config: `docker-compose.yml` (host networking, port 8123, `/config`
bind-mounted from `/home/orangepi/docker-data/homeassistant`).

    http://192.168.2.113:8123    user: freeman    password: in `secrets` (HA_USER / HA_PASS)

The container install has no add-ons (that needs Home Assistant OS). Locked out /
forgot the owner password:

    docker exec homeassistant hass --script auth --config /config list
    docker exec homeassistant hass --script auth --config /config change_password <user> <newpass>
    docker restart homeassistant        # required, the running instance keeps the old hash

The only unrecoverable case is losing the owner account entirely - that means a
fresh onboarding, i.e. losing the config. That is why the password is in
`secrets`.

## iCSee camera (integration + dashboard)

The camera is an XM/iCSee device at `192.168.2.33:34567` (onvif/RTSP on :554),
added through the third-party HACS integration
[`dbuezas/icsee-ptz`](https://github.com/dbuezas/icsee-ptz) **v5.1.6**, installed
at `custom_components/icsee_ptz/` in the HA config (service state - not in git).
The config entry holds the camera credentials; re-add the integration through the
HA UI if it is ever lost (host/port/MAC: `192.168.2.33`, `34567`,
`a4:ef:15:7c:f0:9b`).

### RTSP password patch (required for the live feed)

Upstream percent-encodes the RTSP password. XM parses the URL path verbatim and
does *not* decode it, so a password with `!`, `@`, `#`, ... fails auth and the
live feed shows nothing (verified on hardware: `password=X!` -> 200 OK,
`password=X%21` -> 401). Apply the local patch after installing or upgrading the
integration, then restart HA. The container and the Pi have `git`, not `patch`:

    git -C /home/orangepi/docker-data/homeassistant/custom_components/icsee_ptz \
        apply -p1 /home/orangepi/Github/orangepi5/docker/homeassistant/icsee-ptz-rtsp-password.patch
    docker restart homeassistant

The patch file lives next to this README. Re-check it after every integration
upgrade - upstream may fix it, and the hunk will then fail loudly instead of
silently regressing.

### Camera dashboard

The "Camera" dashboard (`/icsee-camera`) is a storage-mode Lovelace dashboard:
the live main-stream feed (`picture-elements` + `camera_view: live`) with 12
state-icon PTZ/zoom controls overlaid, plus a "Quick controls" card and a
separate "Status" view (camera/network/storage/security entities).

Lovelace config is service state (`.storage/lovelace.icsee_camera`) and is
deliberately not in git. `lovelace.icsee_camera.json` in this directory *is* the
source of truth; re-apply it with:

    sudo ./docker/homeassistant/apply-dashboard.sh

It logs in with `HA_USER` / `HA_PASS` from `secrets` (no token is stored), creates
the dashboard registration if missing, and saves the config through HA's
websocket API. Idempotent - safe to re-run.

### PTZ quirks (verified on this camera)

* **A direction press starts continuous motion; it does not stop by itself.**
  Frames grabbed 1 s and 4 s after a single `ptz_up` press still differ; only
  after `Stop` do they stabilize. Always follow a move with the centre **Stop**
  button. `Stop` is implemented as `DirectionUp` with `Preset: -1`.
* **`step` (0-10, default 2) is the speed, not the distance.** The default 2 is
  usable - a single press already moves the camera visibly - so "it doesn't
  move" means a missing `Stop`, not too small a step. Raise it only for a
  faster pan.
* **The dashboard's home button is `GotoPreset` with preset 0, and it only
  moves if a preset 0 has been stored.** It is not a factory "home", so on a
  fresh camera it does nothing until you set one. Store the current position
  with the `button.icsee_camera_ptz_home_set_current_position` entity (or the
  service, below); after that the home button returns to it. Verified end to
  end - `SetPreset`, pan away, `GotoPreset` restored the framing. Preset 0 is a
  valid slot; the dashboard simply has no "set" button for it.
* **`ZoomTile` / `ZoomWide` are the zoom-in/out commands** (upstream naming).

Test a move directly against the API and grab an RTSP frame before/after to
confirm physical movement (a static scene can hide a real move):

    curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"entity_id":"binary_sensor.icsee_camera_motion_alarm","cmd":"DirectionUp","step":8}' \
      http://192.168.2.113:8123/api/services/icsee_ptz/move
