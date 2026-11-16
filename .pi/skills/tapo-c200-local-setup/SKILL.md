---
name: tapo-c200-local-setup
description: Set up a brand-new TP-Link Tapo C200 camera with no TP-Link cloud account, then bring it into Home Assistant with working PTZ. Use when the user has a factory-fresh or reset Tapo camera (C200/C210 and similar) and wants it fully local - provisioning over the camera's setup AP, RTSP/ONVIF, cloud blocking, a static DHCP lease, and the custom HA integration in docker/homeassistant/tapo-c200. Also use when a Tapo camera's PTZ buttons, presets, or live feed in Home Assistant are broken.
---

# Tapo C200: cloudless setup + Home Assistant with PTZ

Two repos are involved:

- `~/github/tapo-local-setup` - provisioning a factory camera over its setup AP
  (`onboard.sh`, `probe.sh`, `hunt.sh`, `verify.sh`, `find-camera.sh`)
- this repo: `docker/homeassistant/tapo-c200` - the HA integration
  (`custom_components/tapo_c200`) and its README with every API quirk

**Step 0, always: read the pytapo repo** - https://github.com/JurajNyiri/pytapo
(and its issue tracker, especially the open issue about provisioning). Firmware
branches differ (`klap`, `tpap`/SPAKE2+, legacy `pytapo`) and the login scheme
plus error codes change between builds. Everything below is verified on
**C200 hw 5.0, fw 1.2.1 Build 250324** - a newer build may differ. Do not infer
the branch from the label; run `probe.sh` and believe what it reports.

## 1. Know what is (and is not) possible

pytapo **cannot provision** a factory camera - it is a client for an
already-set-up camera. Provisioning happens over the camera's own unauthenticated
`onboarding` API, implemented by the scripts in `tapo-local-setup`.

A fresh camera raises an open AP `Tapo_Cam_XXXX` (XXXX = last 4 of the MAC) and
answers at `https://192.168.191.1` with **no authentication**.

One hard constraint: **the machine doing the setup loses its link to the agent**
while on the camera AP, because that AP has no internet. So either run the setup
detached with a log, or use a second machine with two interfaces (laptop on
Ethernet + Wi-Fi on the camera AP - the approach that worked here).

Android/Termux note: a phone whose Wi-Fi has no internet keeps cellular as the
default route, so traffic to `192.168.191.1` silently leaves via mobile data.
The tell is that pinging your *own* `192.168.191.100` fails. A laptop with an
Ethernet default route does not have this problem.

## 2. Provision

```bash
cd ~/github/tapo-local-setup
./probe.sh 192.168.191.1                 # read-only: protocol + is onboarding open
./onboard.sh 192.168.191.1 '<password>' '<wifi-ssid>'
```

`onboard.sh` runs 7 steps: login with the factory default password, `scanApList`
(also grabs the camera's RSA key), `setOsd`, `setAccountEnabled` +
`changeThirdAccount` (`tapoadmin`), `changeAdminPassword`, re-login, `connectAp`.

Record three facts afterwards:

- **admin account**: `admin` + the password you passed - used by the HTTP API
  (and therefore by pytapo and Home Assistant).
- **third account**: `tapoadmin` + the same password - used by **RTSP and
  ONVIF**. This is the one that matters for the live feed; mixing them up gives
  `401 Unauthorized`.
- camera IP on the LAN, found with `./find-camera.sh 192.168.2`.

The factory-default admin password is model/firmware specific (it was
`TPL075526460603` here, `zMiVw8Kw0oxKXL0` on old C200s). The reset button does
**not** restore it. Only probe a short list - the camera locks you out after
about 10 failed logins.

Script internals worth preserving if you rewrite anything:

- every request needs a strictly increasing `seq` header, and the `tapo_tag` must
  be computed with the **same** sequence that goes in the header (a mismatch is
  `-40401 Invalid stok`). The scripts persist `seq` in a temp file because the
  calls run inside `$( )` subshells.
- `ap_list` / `public_key` nesting varies by firmware - search the JSON instead
  of hardcoding a path.

## 3. Prove it works

```bash
./verify.sh 192.168.2.57 '<admin-password>'    # API: model/fw/mac, RTSP+ONVIF URLs
ffprobe -rtsp_transport tcp -i \
  rtsp://tapoadmin:'<password>'@192.168.2.57:554/stream1   # expect h264 1920x1080
```

## 4. Block the cloud (optional, but this user wants it)

The camera phones home seconds after joining: `security.iot.i.tplinknbu.com`,
`use1-device-cloudgateway.iot.tplinknbu.com`, `use1-cvm-api.iot.tplinknbu.com`,
plus `time.windows.com`.

On this network Pi-hole is the resolver and its global blocking is **off**, so a
normal deny rule would be inert. The working mechanism is `misc.dnsmasq_lines`
with `address=/domain/` lines, which answer NXDOMAIN regardless of the global
switch:

```bash
deny-domain add tplinknbu.com      # on the Pi, from the pihole-local-dns repo
static-lease add a8:29:dc:ab:b5:50 192.168.2.57 C200
```

Be honest with the user: this is **not** airtight. The router is itself a
working resolver, `8.8.8.8` is reachable from the LAN, and the Pi is not the
gateway (no `ip_forward`, no nftables). Airtight needs a gateway-side WAN deny or
an IoT VLAN with no default gateway.

## 5. Home Assistant

Copy the integration and restart - HA caches custom components at startup, so
without the restart adding the integration fails with "Invalid handler
specified":

```bash
scp -r docker/homeassistant/tapo-c200/custom_components/tapo_c200 \
    orangepi@192.168.2.113:/home/orangepi/docker-data/homeassistant/custom_components/
docker restart homeassistant
```

Then add it via the UI, or programmatically over the config-flow REST API
(`POST /api/config/config_entries/flow`, then `POST .../flow/{flow_id}` twice -
step `user`, then step `rtsp`). There is no websocket command for this; the REST
routes are the ones that exist. Two steps, and **both** account types are needed:

1. host + `admin` + admin password
2. `rtsp_username: tapoadmin` + the same password

On the Orange Pi, `docker` works without sudo (the user is in the `docker`
group); `sudo` over ssh needs the password piped with `sudo -S -p ""`, and
credentials come from `octx creds get common`. Never commit a password.

## 6. PTZ: the part not in pytapo's docs

Namespace split on this firmware - **reads under `ptz`, movement under `motor`**:

- `Tapo.getMotorCapability()` fails (`motor.capability` -> `-40101`). Use the raw
  request `{"method":"get","ptz":{"name":["capability"]}}`.
- Position: `{"method":"get","ptz":{"name":["status"]}}` -> `angle_x` (0-360,
  wraps), `angle_y` (signed, about -15..55 on this unit).
- `moveMotorStep(direction)` is a **direction selector**, not a distance:
  90 = up, 270 = down, 0 = clockwise, 180 = counter-clockwise. Verified by
  reading the angles around each call - re-verify on a different model rather
  than assuming.
- `-64304` = at the end of travel (normal), `-64303` = motor busy,
  `-64302` = preset missing.
- Presets use their own namespace: get `{"preset":{"name":["preset"]}}`, save
  `{"preset":{"set_preset":{"name":N,"save_ptz":"1"}}}`, delete
  `{"preset":{"remove_preset":{"id":[..]}}}`. Maximum 8.

Home Assistant traps that cost real time:

- **`Tapo(...)` logs in inside `__init__`** and its `AsyncHandler` runs its own
  loop, so constructing it on HA's loop thread raises
  `RuntimeError: Cannot run the event loop while another loop is running`.
  Build the client **inside the executor**.
- A `CoordinatorEntity` **never gets `async_update`** - read `coordinator.data`.
- `async_request_refresh()` is debounced by 10 s; use `async_refresh()` after
  writes.
- A PTZ step takes about 2 s, so re-read the position **after a delay** or the
  sensor shows the previous angle.
- `camera_proxy` answers 500 unless `use_stream_for_stills` is `True` when
  `async_camera_image` returns `None`.
- `getSDCard()` returns `[{"hd_info_1": {...}}]`; no card means
  `status: offline`.
- Unsupported here: `getAlarmConfig` (-40210), `getEvents` (-71114). The motion
  entity therefore reports the setting, not live motion.

## 7. Give it a dashboard

The camera also needs its own sidebar dashboard - otherwise it only shows up as
an entity card under the auto-generated Security dashboard, with no PTZ
controls, and the user will report "I don't see any PTZ controls".

`docker/homeassistant/lovelace.tapo_camera.json` is the source of truth for a
`/tapo-camera` dashboard (live feed + 5-button PTZ overlay + quick controls);
`apply-dashboard.sh <slug>` pushes it through HA's websocket API, creating the
sidebar registration and fixing the title/icon if they drift. The overlay
toggle needs `input_boolean.tapo_ptz_controls_visible` in
`configuration.yaml` - add it before the dashboard, or the toggle card is dead.

PTZ overlay differs from iCSee's on purpose: 5 buttons (up/down/left/right +
calibrate), because the C200 has no optical zoom, no diagonal move, and no
continuous-motion `stop` - a press is a fixed step, so nothing needs stopping.

## 8. Verify in Home Assistant

```bash
# stills must be real JPEGs, with the camera's OSD clock burnt in
curl -s -H "Authorization: Bearer $TOKEN" \
  http://192.168.2.113:8123/api/camera_proxy/camera.tapo_camera_sub_stream -o /tmp/t.jpg
```

The OSD timestamp changing between two snapshots is the fastest proof the frame
is live. If the image says "Privacy Mode is on", a previous test left it on -
turn `switch.tapo_camera_privacy_mode` off.

Press a PTZ button, wait about 6 s, and confirm `sensor.tapo_camera_tilt_angle`
changed. The button may legitimately fail with "already at the end of its
travel" at a limit - that is correct behaviour, not a bug.

## Never

- Never put a password, PSK, or token in a repo file, README, log line, or
  skill. Read them from `octx creds get <name>` or the gitignored `secrets`.
- Never `rm -rf` on this user's machines without being asked - overwrite in place
  with `cp`, or `mv` aside to a timestamped path.
- Never touch `custom_components/icsee_ptz` - a separate camera, patched
  locally, that must keep working.
