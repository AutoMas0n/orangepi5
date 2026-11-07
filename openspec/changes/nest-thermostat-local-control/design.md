# Design

> STATUS: **parked exploration.** Findings captured 2026-11-07. No decision made.
> Written so we can resume without re-researching. See `proposal.md` for the
> framing and the two candidate paths.

## Context

Current state, as verified on 2026-11-07:

```
Orange Pi 5  (192.168.2.113, end0)
  |
  +-- Docker
  |     +-- homeassistant  ghcr.io/home-assistant/home-assistant:stable
  |     |      Home Assistant 2026.11.0
  |     |      network_mode: host        (deliberately NOT behind gluetun)
  |     |      /home/orangepi/docker-data/homeassistant -> /config
  |     +-- gluetun (healthy), qbittorrent, jackett, stremio
  |
  +-- :8123  Home Assistant     :55055 Lila Tracker     :22 sshd

Nest Learning Thermostat (3rd gen)   192.168.2.68
  MAC cc:a7:c1:32:19:b5   (matches the Wi-Fi MAC reported by the user)
  ports 80 / 443 / 8080 / 9543 / 11095  ->  ALL closed
```

Verified Home Assistant inventory:

- `automations.yaml` is **empty** (2 bytes).
- `custom_components/` contains exactly one component: `icsee_ptz` (a locally
  developed iCSee camera/PTZ integration).
- Config entries: sun, backup, analytics, **marketplace**, cast, met, songpal,
  icsee_ptz — **no nest, no matter, no thread, no bluetooth, no zha/zwave, no hacs**.
- **HACS is not installed.** There is a `marketplace` config entry and a
  `.storage/marketplace.repositories` with ~6194 cached HACS manifests, but that is
  HA's built-in catalog integration, not HACS. No nest/thermostat/Matter entry is
  in that cache.
- The thermostat exposes **no local service** at all — there is no local http/api
  surface to talk to. Any HA integration must go through Google's servers.

Constraints / facts that shape the options:

- **The Nest Learning Thermostat (3rd gen) does not support Matter.** Google shipped
  Matter only to the Nest Thermostat (2020) and the Learning Thermostat (4th gen).
  Matter on Nest is *also* cloud-dependent (thermostat checks for internet on boot;
  without it all smart functionality including Matter is disabled).
- HA's built-in `nest` integration uses Google's **SDM API** and costs a one-time
  **US$5** Device Access fee, plus a Google Cloud project, OAuth, and a Device
  Access project. The user does not want to pay this.
- **OpenSpec in this repo is empty**: `openspec/specs/` and `openspec/changes/`
  had no content before this change. There is no existing HA configuration in the
  repo besides `docker/homeassistant/docker-compose.yml`.

## Goals / Non-Goals

**Goals**

- Home Assistant is the single source of truth for the heating setpoint.
- A hysteresis band (e.g. +/- 0.5 C around target) prevents short-cycling and
  removes dependence on the thermostat's vendor-side scheduling.
- Avoid Google's $5 Device Access fee (and, if Path B, avoid Google entirely).
- Keep it cheap and low-maintenance; prefer boring, well-supported components.

**Non-Goals**

- Reverse-engineering or rooting the Nest. The known local-firmware projects
  (NoLongerEvil, Hearth, retherm, badnest) are **verified on Gen 2 only**; no
  confirmed end-to-end Gen 3 install exists, and the original DFU entry point is a
  2014 exploit predating this hardware. Explicitly out of scope.
- A full smart-home platform build-out (Zigbee/Z-Wave ecosystems) beyond what one
  thermostat needs.
- Keeping the Nest's "learning" feature in any form. It was disabled by the user;
  it is not wanted back.

## Decisions

*(Provisional — nothing is committed. These are the current leanings so far.)*

### D1. HA owns the setpoint; the thermostat becomes a dumb actuator

Rationale: the whole point of the change. Whatever hardware path is chosen, the
thermostat's own schedule/Eco/Home-Away Assist must be off, or the two controllers
will fight and oscillate.

### D2. (Path A) Free unofficial Nest API via `tronikos/nest_legacy`, not SDM

Alternatives considered:

| Option | Verdict |
|---|---|
| Google SDM (`nest` integration) | Rejected: $5 + Cloud project + OAuth + consent screens. |
| `tronikos/nest_legacy` | **Current lean.** Free, HACS-default, actively maintained (v0.8.1, 2026-10-24; commits into Nov 2026). Docs list "1st, 2nd, 3rd gen, Thermostat E, 2020 mirror edition". Issue #38 is a 3rd-gen Learning user. Uses the same unofficial API the Nest app uses (REST streaming + Protobuf), supports push updates and full climate controls. |
| Root/self-host firmware | Rejected: Gen-3 unproven, high risk, EOL of official support. |

Known catch: authentication requires harvesting `issue_token` + cookies, and **must
be done in Firefox or Safari, not Chrome/Edge/Brave** (Device Bound Session
Credentials bind the session to the device and break copied cookies within hours).
A companion Firefox extension (`tronikos/nest-token-extractor`) automates it. The
integration persists Google's rotated cookies across HA restarts.

### D3. (Path B) Prefer a genuinely local thermostat over a cloud one

If "Google not in the loop at all" is the real requirement, then the honest answer
is a hardware swap. Candidates found, in CAD:

**If the system is 24V low-voltage (central forced air / heat pump):**

| Device | Price (CAD) | HA integration | Truly local? | BS factor |
|---|---|---|---|---|
| Honeywell T6 Pro Z-Wave (TH6320ZW) | ~$90–140 | `zwave_js` | Yes + Z-Wave stick (~$40–60) | none — no account |
| Venstar T7850/T2000 | ~$150–260 | `venstar` (built-in) | Yes — built-in local API, Skyport optional | none if Skyport skipped |
| Matter thermostat (Meross/Aqara/Bosch) | ~$80–200 | `matter` | Yes + Thread border router | none |
| ecobee Essential | **$179.99** | `ecobee` (cloud) | No — HA signs into ecobee.com | account required, but $0 fee |
| ecobee Enhanced | $249.99 | `ecobee` | No | same |
| ecobee3 lite (refurb) | $149.99 | `ecobee` | No | same |
| ecobee Premium | $329.99 | `ecobee` | No | same |

**If the system is line-voltage (baseboard / in-floor):**

| Device | Price (CAD) | HA | Local? |
|---|---|---|---|
| Sinope TH1123ZB | ~$115–125 | `zha` (Zigbee) | Yes — needs Zigbee coordinator (~$25–40) |
| Sinope TH1143WF | $99.99–124.99 | `neviweb` | No — cloud |
| Mysa (baseboard Gen3) | $159.00 | Matter | Yes, if Matter/Thread |

Notes:
- The ecobee integration no longer needs a developer API key (since HA 2026.3) —
  just username/password. It is the direct analogue of `nest_legacy`: free,
  official, still somebody else's server.
- Venstar is the "boring but correct" pick: first-class local API, no account.
- Honeywell T6 Z-Wave is the cheapest genuinely-local route; cost is the Z-Wave
  USB stick.
- Cheap genuinely-local options cost roughly the same as the free-but-cloud path
  once the coordinator is included, so "cost-effective" and "no third party" point
  the same direction here.

### D4. Hysteresis implementation approach (not yet chosen)

HA's built-in `generic_thermostat` **cannot drive the Nest directly**: its
`heater:` option requires a *toggle switch* entity, not a climate entity. Options:

| Option | Notes |
|---|---|
| (a) Plain automation | Read temp, write setpoint to the far end of the band. ~20 lines, no dependencies. Simplest and likely sufficient. |
| (b) `ScratMan/HASmartThermostat` | PID/PWM, 543 stars, active (Oct 2026). Docs show `heater:` accepting another climate entity for cascaded outer/inner loops; `pwm: 0` gives pure hysteresis. Needs HACS. |
| (c) Custom | Full control, more code to maintain. |

Note: some local thermostats (Venstar, Honeywell T6) have their **own adjustable
deadband**, which may make the HA-side band unnecessary.

## Risks / Trade-offs

- **[Nest's own automation fights HA]** → Strip the Nest schedule, Eco,
  Home-Away Assist, and auto-schedule before layering HA control. This is the
  *actual* de-enshittification step and it is free.
- **[`nest_legacy` is an unofficial API]** → Google could change it and break the
  integration until the maintainer patches. Mitigation: pin a known-good version,
  watch the repo. Accepted risk for Path A.
- **[Cookie/token fragility]** → Must use Firefox/Safari for extraction; Chrome
  credentials die within hours (Device Bound Session Credentials). One-time setup.
- **[HACS is not installed]** → Any custom integration needs HACS added first, or
  a manual `custom_components/` drop-in. Small extra step.
- **[Radio dongles need container privileges]** → Adding Zigbee/Z-Wave to the HA
  container requires `privileged: true` and device passthrough, plus
  `docker compose up -d --force-recreate`. The existing compose file already
  documents this for Bluetooth/Zigbee.
- **[Cost of being wrong]** → Buying hardware for the wrong wiring class (24V vs
  line-voltage). Resolve the open question below before purchasing.
- **[Nest becomes e-waste]** (Path B) → Sell or repurpose; no local firmware route
  for Gen 3.

## Migration Plan

Not applicable yet — no deployment is committed. Whichever path is chosen, the
sequence is expected to be:

1. Resolve the two blocking questions below.
2. (Path A) Install HACS if needed, add `nest_legacy`, authenticate with Firefox.
3. (Either) Strip the Nest's own schedule/Eco/auto-schedule.
4. (Either) Implement the hysteresis band via option (a) or (b).
5. (Path B) Add the radio dongle, rewire, pair the new thermostat.

Rollback: reverse the HA configuration change; the existing docker-compose and
`/config` are untouched except for the new integration/automation entries.

## Open Questions

**BLOCKING — must be answered before specs or tasks are written:**

1. **What does the Nest currently control?** 24V low-voltage central HVAC
   (furnace/AC/heat pump) or line-voltage baseboard/in-floor? This decides the
   entire hardware category and which price list applies.
2. **Which "spite" is it?** "Do not pay Google a fee" (then Path A / `nest_legacy`
   wins at $0 and is sufficient) or "Google must not be in the loop at all"
   (then it is a hardware swap, and the Honeywell T6 Z-Wave / Sinope ZB is the
   value pick)?

**Deferrable:**

3. Hysteresis implementation: plain automation (a) vs `HASmartThermostat` (b)?
4. Do we want the thermostat replacement captured as repo config (compose changes)
   or purely as Home Assistant configuration outside the repo?

## Appendix — Research Trail

- HA `nest` integration docs: SDM API, $5 Device Access fee, Workspace/Advanced
  Protection incompatibility, Pub/Sub setup.
- HA `matter` / `homekit_controller` docs: Thread border router requirement
  (Nest Hub 2nd gen, Nest Wi-Fi Pro, HomePod mini, HA OpenThread).
- HA `venstar`, `zwave_js`, `esphome`, `zha`, `ecobee`, `smartthings` docs.
- Google Nest device identification: support.google.com/googlehome/answer/9246551.
- Google end-of-support: support.google.com/googlehome/answer/16233096 — 1st/2nd
  gen Learning EOL 2025-10-25; 3rd gen unaffected; 4th gen security updates to at
  least 2029-08-20.
- `tronikos/nest_legacy` (GitHub) — free unofficial Nest API integration.
- `tronikos/nest-token-extractor` — Firefox extension for credential extraction.
- `ScratMan/HASmartThermostat` — PID/PWM thermostat for HA.
- Google Nest thermostat rooting: `wiki.exploitee.rs` (2014 GTVHacker DFU exploit),
  `codykociemba/NoLongerEvil-SelfHosted`, `nolongerevil.com`,
  `cjdell/nest-firmware-custom`, `tylxr59/Hearth`, `jiggak/retherm`,
  `cjserio/nest-thermostat-protocol-docs` (Gen 2 focus), `elparko/Nest2`,
  `mattsmallman/badnest` (archived), `openweave/openweave-core`.
