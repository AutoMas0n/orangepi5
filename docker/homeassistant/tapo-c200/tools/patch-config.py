#!/usr/bin/env python3
"""One-off: add the zoom input_select and the card-mod frontend module.

Idempotent - re-running will not duplicate either block. Backs the file up
first, and refuses to write anything if the result fails a YAML parse.
"""
import shutil
import sys
import time  # noqa: F401 - used for the backup suffix

import yaml

# Inside the HA container the config dir is mounted at /config, so this script is
# normally run with `docker exec homeassistant python3 ... /config/configuration.yaml`.
PATH = sys.argv[1] if len(sys.argv) > 1 else "/config/configuration.yaml"

INPUT_SELECT = """
  tapo_camera_zoom:
    name: Tapo zoom
    icon: mdi:magnify
    options:
      - "1x"
      - "2x"
      - "3x"
"""

with open(PATH) as f:
    text = f.read()

changed = []

# 1. extra_module_url for card-mod, as the first child of the frontend: block.
if "extra_module_url" not in text:
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.startswith("frontend:"):
            lines.insert(
                i + 1,
                "  extra_module_url:\n  - /local/card-mod.js\n",
            )
            break
    else:
        sys.exit("no frontend: block found")
    text = "".join(lines)
    changed.append("frontend.extra_module_url")

# 2. The zoom selector.
if "tapo_camera_zoom" not in text:
    if "\ninput_select:" in text:
        text = text.replace(
            "\ninput_select:\n", "\ninput_select:\n" + INPUT_SELECT, 1
        )
    else:
        text = text.rstrip("\n") + "\n\ninput_select:" + INPUT_SELECT
    changed.append("input_select.tapo_camera_zoom")

if not changed:
    print("nothing to do - already present")
    sys.exit(0)


class _Tolerant(yaml.SafeLoader):
    """HA configs use !include/!secret/!env_var - ignore the tags, parse the rest."""


def _any_tag(loader, suffix, node):  # noqa: ARG001
    return None


_Tolerant.add_multi_constructor("!", _any_tag)

try:
    yaml.load(text, Loader=_Tolerant)  # noqa: S506 - safe loader subclass
except yaml.YAMLError as err:
    sys.exit(f"REFUSING to write: result is not valid YAML\n{err}")

shutil.copy2(PATH, f"{PATH}.bak-{int(time.time())}")
with open(PATH, "w") as f:
    f.write(text)
print("changed:", ", ".join(changed))
