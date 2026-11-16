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

The dashboard for these lives in the parent directory:
`docker/homeassistant/lovelace.tapo_camera.json`, applied to `/tapo-camera` by
`apply-dashboard.sh tapo_camera`. Its PTZ overlay is a 5-button pad (up, down,
left, right, calibrate) rather than iCSee's 12 - the C200 has no optical zoom
and no diagonal move. It also has no `stop`, but not for iCSee's reason: these
buttons use `moveMotor(x, y)`, a **finite relative move in degrees**, so a press
ends by itself. Never wire them to `moveMotorStep(direction)` - that starts a
continuous sweep which no command can stop (measurements in
`../README.md`'s PTZ section).

The overlay is a centred 3x3 pad at a fixed 52 px pitch with 44 px round hit
areas instead of percentage positions: on a ~350 px phone card a 7% gap is only
~25 px, which made the buttons collide. The controls toggle is a compact
`entities` row, not a `button` card - that renders as a huge tile on mobile.

Buttons are translucent (`rgba(0,0,0,0.18)`) so the live picture stays readable
under them. The centre button cycles **zoom 1x -> 2x -> 3x -> 1x**.

### Zoom is digital, because the hardware has none

This camera has a **fixed lens**. `getZoomConfig`, `getDigitalZoom`,
`setDigitalZoom`, `getPtzZoom`, `getLensZoomConfig` and `zoom` all answer
`-40210 METHOD_DO_NOT_EXIST`, and `basic_info` contains no zoom field. There is
no camera-side zoom to call, so the zoom is done in the browser:

* `input_select.tapo_camera_zoom` holds `1x | 2x | 3x`. The centre button is a
  `state-icon` bound to it with `tap_action: perform-action
  input_select.select_next` - `select_next` wraps `1x -> 2x -> 3x -> 1x` on its
  own, so no script or automation is needed.
* `card-mod` scales the live `<hui-image>` to match, with a 220 ms transition:

```yaml
card_mod:
  style: |
    hui-image {
      transform: scale({% set z = states('input_select.tapo_camera_zoom') %}
        {% if z == '3x' %}3{% elif z == '2x' %}2{% else %}1{% endif %});
      transform-origin: center center;
      transition: transform 220ms ease-in-out;
    }
    :host { overflow: hidden; }
```

`hui-image` is a real child of the picture-elements card (confirmed in the
bundled frontend), so the transform hits only the image - the buttons stay put.
`overflow: hidden` keeps the scaled stream inside the card instead of bleeding
over the dashboard.

card-mod is a **single local file**, no HACS: download `card-mod.js`, drop it in
`www/`, and add `/local/card-mod.js` to `frontend.extra_module_url`. Both
`tools/patch-config.py` and `tools/restyle-ptz.py` in this directory do those
edits idempotently - re-running either is safe.

Calibrate (`button.tapo_camera_calibrate_motor`) moved off the centre button and
into the controls row, so it is still reachable.

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

## Firmware 1.4.6 broke PTZ reads — turn auto-upgrade off

The camera **auto-upgraded itself** from `1.2.1 Build 250324` to `1.4.6 Build
260709` overnight (auto-upgrade was `enabled: "on", time: 03:00`). Screenshot
and motion kept working; **PTZ position reads died** and the integration's
pan/tilt sensors went permanently `unknown`.

What 1.4.6 changed:

* The anonymous namespace form is gone: `{"method":"get","ptz":{...}}` now
  answers `-40210` METHOD_DO_NOT_EXIST. Same for `device_info`, `system`, etc.
* Named camelCase methods replaced it: `getDeviceInfo`, `getOsd`,
  `getLedStatus`, `getLensMaskConfig`, `getTime`→`getClockStatus`,
  `getSDCard`→`getSdCardStatus`. pytapo's high-level reads still work because
  it already uses named methods.
* **`getPtzStatus` exists but always returns an empty result.** Brute-forced
  across every section (`ptz`, `ptz_status`, `motor`, `status`, …), every name
  (`status`, `all`, `angle_x`, …), and index/channel variants — all empty.
  *There is no way to read the pan/tilt angle on this firmware.* Upstream pytapo
  has no support for it either (no matching issue, and the official
  HomeAssistant-Tapo-Control has no angle sensor at all).
* **Movement still works.** `moveMotor(x, y)` returns `{}` and physically
  moves, so the buttons are fine — only the *read* is gone.
* ONVIF (port 2020) cannot fill the gap: WS-Security UsernameToken auth
  succeeds (HTTP Basic is rejected with 400), but `GetStatus` returns an empty
  `PTZStatus` with no Pan/Tilt/Zoom.

The integration therefore probes once at setup and **does not create the angle
sensors** when the camera will not report a position (`position_readable` in
`__init__.py` / `device.py`), rather than leaving two entities stuck at
`unknown`. Delete stale registry entries after a downgrade/upgrade.

**Disable auto-upgrade** or the API can silently change again under you.
`setFirmwareAutoUpgradeConfig(enabled=False)` fails with a bogus `-40209`
"Invalid login credentials" unless a time is supplied with it — this works:

```python
cam.setFirmwareAutoUpgradeConfig(enabled=False, time="03:00")  # -> {}
```

## PTZ: what the API actually is on this firmware

Verified against C200 **hw 5.0, fw 1.2.1 Build 250324** (the PTZ calls below
are the 1.2.x ones — see the firmware section above for what 1.4.6 removed).
This is the part pytapo does not document, and it is why the stock
`Tapo.getMotorCapability()` fails here.

* Reads live under the **`ptz`** namespace, movement commands under **`motor`**.
  `Tapo.getMotorCapability()` requests `motor.capability` and gets `-40101`;
  the raw request that works is
  `{"method":"get","ptz":{"name":["capability"]}}`.
* Position: `{"method":"get","ptz":{"name":["status"]}}` ->
  `angle_x` (0-360, wraps), `angle_y` (signed, roughly -15..55 on this unit).
* **`moveMotorStep(direction)` is unusable for a button: it starts a
  continuous sweep that never stops by itself.** One call at direction `0`
  swept `angle_x` 162 -> 208.5 -> 259.1 -> 311.2 -> 340.0 (the hard limit) at
  about 50 deg/s and stayed there. There is no stop command - `moveMotor(0,0)`
  answers **-64304** mid-travel and does not halt the motor, every `ptz` write
  shape returns **-40101**, and `motorStop` / `stopMotor` / `manualStop` desync
  the transport (the camera replies with a `BadStatusLine` on the next POST).
  Recovery is `setPreset(<id>)` or waiting for the limit.

* **`moveMotor(x, y)` is a finite *relative* move in DEGREES** and is the
  primitive the buttons use. Verified to the hundredth of a degree:
  `moveMotor(20, 0)` -> `angle_x` +20.00, `moveMotor(0, -5)` -> `angle_y`
  -5.00, `moveMotor(-15, 0)` -> -15.00. `+y` is up, `+x` pans clockwise seen
  from above. It settles in about a second and holds. The integration nudges
  15 deg in pan and 10 deg in tilt (`PTZ_NUDGE_DEGREES` /
  `PTZ_TILT_NUDGE_DEGREES` in `const.py`).

* At the end of travel the camera answers **-64304** "Maximum Pan/Tilt range
  reached (MOTOR_LOCKED_ROTOR)". That is normal, not a fault: the button
  surfaces a translatable "already at the end of its travel" error instead of a
  raw exception. **-64303** is motor busy, **-64302** preset not found.
* Presets are their own namespace: get via
  `{"preset":{"name":["preset"]}}`, save via
  `{"preset":{"set_preset":{"name":..., "save_ptz":"1"}}}`, delete via
  `{"preset":{"remove_preset":{"id":[...]}}}`. Max 8 presets.
* A nudge takes about a second to travel and report, so the integration re-reads
  the position after a delay instead of immediately (see below).

* The capability block (`ptz.capability`) reports
  `absolute_move_supported`, `relative_move_supported`,
  `continuous_move_supported` all `1`, `position_pan_range` /
  `position_tilt_range` `[-1, 1]`, and `beyond_move_range` `[-4, 4]`. The
  absolute form is not reachable from pytapo: a raw `motor.move` with
  `x_coord`/`y_coord` floats returns `-40407` and poisons the session, so only
  the relative `moveMotor` path is safe to call.

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

## Keeping it off the internet (and still telling the time)

A DNS block alone does not do this. This camera **upgraded its own firmware
while every TP-Link domain was NXDOMAIN**, because it had a real gateway and
could resolve or reach things through `192.168.2.1`. DNS blocking is advisory;
taking the gateway away is not.

But a device with no gateway has no NTP either, and this camera has **no
way to be told its NTP server**: `getNtpConfig`/`setNtpServer` do not exist on
1.4.6. Left alone it falls back to its firmware build time - it sat at
`2026-07-09 08:42` (build date) with every OSD timestamp and recording date
wrong.

So: **the Pi becomes the camera's gateway and forwards only NTP.**

```bash
ssh pi@192.168.2.222 'offline-device add a8:29:dc:ab:b5:50 192.168.2.57 C200'
ssh pi@192.168.2.222 'offline-device status'   # rules + hit counters
```

Three pieces, all in `network/`:

1. Pi-hole DHCP tags this MAC (`dhcp-option=tag:cam,3,192.168.2.222`) so the
   camera is offered the Pi as its gateway, and option 42 points NTP there too.
2. `network/camgw.nft` forwards `udp/123` and **rejects everything else**, with
   counters - so attempts are visible rather than silent.
3. `network/camgw.service` re-applies the rules at boot. It is a separate unit
   on purpose: `/etc/nftables.conf` starts with `flush ruleset`, and enabling
   that service would wipe Docker's rules on the Pi.

Also set `auto_upgrade.common.enabled = off` (see below) - defence in depth,
not a substitute.

**After adding the tag the camera must renew its lease** (reboot it) before it
uses the new gateway - otherwise it keeps the router and the block does nothing.

Verify it took effect:

```bash
ssh pi@192.168.2.222 'offline-device status'          # reject counter climbing
# camera clock should match the host, not the build date:
#   camera: 2026-11-16 16:41   host: 2026-11-16 11:41 (EST)
```

Remove with `offline-device remove <mac>` - restores the router gateway and
deletes the nft table and unit.

## Moving the camera to another Wi-Fi network

No app and no Tapo account needed. The camera stays provisioned: the admin
password, third account (RTSP), presets and timezone all move with it.

```bash
# 1. What can it see? (2.4 GHz only - the C200 has no 5 GHz radio)
python3 network/migrate-wifi.py --host 192.168.2.57 --password PW --list

# 2. Prove the SSID and PSK without committing
python3 network/migrate-wifi.py --host 192.168.2.57 --password PW \
        --ssid NEW --psk PSK --dry-run

# 3. Switch
python3 network/migrate-wifi.py --host 192.168.2.57 --password PW \
        --ssid NEW --psk PSK
```

Run it from anywhere with `pytapo` + `cryptography` - the HA container already
has both (`docker exec homeassistant python3 /tmp/migrate-wifi.py …`).

How it works: `scanApList` returns the visible networks **and the camera's RSA
public key**; `connectAp` takes the chosen AP entry with the PSK RSA-encrypted
(`unique_key: 1`). Same call the phone app uses during setup, and it still works
once the camera is provisioned.

**Use `--dry-run` first.** A wrong SSID or PSK sends the camera off the old
network with nowhere to go; it then falls back to its own setup AP
(`Tapo_Cam_B550`), so recovery means joining that from a laptop and re-running
the script - or pressing reset, which is the thing to avoid.

Afterwards: find it on the new network (`hunt.sh`, or the DHCP lease table by
MAC), then update the static lease on that network's DHCP server and the Home
Assistant entry if the IP changed (the integration stores the host address).

Not yet exercised end-to-end here: the final `connectAp` was verified only up to
`--dry-run` against a live AP. The scan, target selection, RSA encryption and
the whole argument path are proven.

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
