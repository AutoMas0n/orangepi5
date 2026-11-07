# Proposal

> STATUS: **HALF-BAKED / PARKED.** This is a note-to-self so the exploration can be
> resumed later. **No decision has been made and no work is committed.** See
> `design.md` for full findings and open questions. Likely superseded or heavily
> rewritten once the two open questions are answered.

## Why

We have a Nest Learning Thermostat (3rd gen) that is entirely tied to Google's
cloud, and its advertised "learning" auto-schedule was found useless in practice
(it was disabled; temperature is only ever set explicitly by hand). The goal is
for Home Assistant on the Orange Pi to own the setpoint with a simple hysteresis
band, without paying Google a $5 Device Access fee "out of spite" — and possibly
without Google being in the loop at all.

Two candidate directions exist and are not yet chosen:

- **Path A — keep the Nest**, drive it from HA via a free unofficial integration
  (`tronikos/nest_legacy`), strip the Nest's own scheduling/Eco, and implement the
  hysteresis band in HA. Cost ~$0. Google still in the loop, no fee.
- **Path B — replace the thermostat** with a genuinely local device (Z-Wave,
  Zigbee, Matter, or local-API Wi-Fi). Cost ~$90–260 CAD plus possibly a radio
  dongle. No third party at all.

## What Changes

(Provisional — the scope depends on the open questions in `design.md`.)

- Introduce HA-owned setpoint control with a hysteresis band for the home's
  heating, replacing reliance on the thermostat's own schedule.
- Ensure the thermostat's built-in automation ("learning", Eco, Home-Away Assist,
  auto-schedule) is neutralized so it does not fight HA.
- Optionally: add a local-access radio (Zigbee/Z-Wave/Thread) to the HA host, if
  Path B is chosen. This may require `privileged: true` and device passthrough in
  `docker/homeassistant/docker-compose.yml`.
- **Not yet decided:** whether the Nest stays (Path A) or is replaced (Path B).

## Capabilities

### New Capabilities

- `climate-control`: Home Assistant is the single source of truth for the heating
  setpoint, applying a hysteresis band around a target temperature, and exposing
  the heating state so it can be reasoned about (dashboards, notification, etc.).

  **PROVISIONAL.** No spec delta is written yet (the change sets `skip_specs: true`).
  The requirements are not knowable until the two blocking questions in `design.md`
  are answered — they decide *which* actuator the band drives and therefore what
  the capability actually has to do.

### Modified Capabilities

None — this repo currently has no specs.

## Impact

- **Home Assistant** on the Orange Pi (`192.168.2.113`), version 2026.11.0:
  new HA configuration (integration + automation/script) under
  `/home/orangepi/docker-data/homeassistant/`.
- **HACS is not installed** today, so a custom integration or HACS component would
  need HACS added first (or a manual `custom_components/` drop-in).
- **Nest Learning Thermostat (3rd gen)**, `192.168.2.68`: either integrated via an
  unofficial API (Path A) or replaced by new hardware (Path B).
- **Possibly** `docker/homeassistant/docker-compose.yml` (USB/radio passthrough).
- No impact on the rest of the stack (gluetun, qbittorrent, jackett, stremio).
