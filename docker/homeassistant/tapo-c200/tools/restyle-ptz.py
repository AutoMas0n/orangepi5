#!/usr/bin/env python3
"""Make the PTZ overlay translucent and turn the centre button into a zoom cycle.

Zoom is DIGITAL: this camera has a fixed lens (getZoomConfig / setDigitalZoom /
getPtzZoom all answer -40210), so there is no camera-side zoom to call. The
centre button cycles input_select.tapo_camera_zoom 1x -> 2x -> 3x -> 1x, and
card-mod scales the live image to match.

Idempotent: re-running produces the same file.
"""
import json
import sys

PATH = "/data/data/com.termux/files/home/github/orangepi5/docker/homeassistant/lovelace.tapo_camera.json"

# Translucent, not invisible: the icon still needs to read over a bright frame.
BG = "rgba(0,0,0,0.18)"
BORDER = "1px solid rgba(255,255,255,0.22)"
BG_ACTIVE = "rgba(0,0,0,0.35)"

CARD_MOD = """
hui-image {
  transform: scale({% set z = states('input_select.tapo_camera_zoom') %}{% if z == '3x' %}3{% elif z == '2x' %}2{% else %}1{% endif %});
  transform-origin: center center;
  transition: transform 220ms ease-in-out;
}
:host { overflow: hidden; }
"""


def zoom_jinja(attr: str) -> str:
    """The current level, for an icon/label that follows the selector."""
    return "{{ states('input_select.tapo_camera_zoom') }}"


def restyle(element: dict) -> None:
    style = element.setdefault("style", {})
    if element.get("entity", "").startswith("button."):
        style["background"] = BG
        style["border"] = BORDER


def main() -> int:
    with open(PATH) as f:
        dash = json.load(f)

    ptz_cards = [
        card
        for card in dash["views"][0]["cards"]
        if card.get("type") == "conditional"
        and card.get("card", {}).get("type") == "picture-elements"
    ]
    if not ptz_cards:
        sys.exit("no picture-elements card found - layout changed?")

    for card in ptz_cards:
        inner = card["card"]
        inner["card_mod"] = {"style": CARD_MOD}

        for el in inner.get("elements", []):
            restyle(el)

        for el in inner.get("elements", []):
            if el.get("entity") != "button.tapo_camera_calibrate_motor":
                continue
            # Centre button becomes the zoom cycle. select_next wraps
            # 1x -> 2x -> 3x -> 1x on its own, so no script is needed.
            el["entity"] = "input_select.tapo_camera_zoom"
            el["type"] = "state-icon"
            el["icon"] = "mdi:magnify-plus-outline"
            el["title"] = "Zoom (1x → 2x → 3x)"
            el["state_color"] = False
            el["tap_action"] = {
                "action": "perform-action",
                "perform_action": "input_select.select_next",
                "target": {"entity_id": "input_select.tapo_camera_zoom"},
            }
            # Show the level inside the button instead of a static icon.
            el["style"]["--mdc-icon-size"] = "22px"

    # Calibrate must stay reachable - it lived on that centre button.
    def ent_id(entry):
        # entities entries are "domain.entity" strings or {"entity": ...} dicts
        return entry if isinstance(entry, str) else entry.get("entity")

    for card in dash["views"][0]["cards"]:
        if card.get("type") == "entities" and any(
            ent_id(e) == "input_boolean.tapo_ptz_controls_visible"
            for e in card.get("entities", [])
        ):
            ids = [ent_id(e) for e in card["entities"]]
            if "button.tapo_camera_calibrate_motor" not in ids:
                card["entities"].append(
                    {
                        "entity": "button.tapo_camera_calibrate_motor",
                        "name": "Calibrate motor",
                        "icon": "mdi:crosshairs-gps",
                    }
                )
            if "input_select.tapo_camera_zoom" not in ids:
                card["entities"].append(
                    {
                        "entity": "input_select.tapo_camera_zoom",
                        "name": "Zoom",
                        "icon": "mdi:magnify",
                    }
                )

    with open(PATH, "w") as f:
        json.dump(dash, f, indent=2)
        f.write("\n")
    print(f"updated {len(ptz_cards)} picture-elements card(s)")
    print("overlay:", BG, "| centre button: zoom cycle | calibrate moved to the controls row")
    return 0


if __name__ == "__main__":
    sys.exit(main())
