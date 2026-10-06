#!/bin/bash
# Re-apply the "Camera" Lovelace dashboard from lovelace.icsee_camera.json.
#
# The dashboard lives in HA's storage (.storage/lovelace.icsee_camera), which is
# service state and is deliberately not in git. This script is the reproducible
# half: it saves docker/homeassistant/lovelace.icsee_camera.json through Home
# Assistant's own websocket API, so it survives an HA reset without hand-editing
# .storage.
#
# Credentials come from the gitignored `secrets` file (HA_USER / HA_PASS). No
# long-lived token is stored anywhere. Idempotent: safe to run any time.
#
# Usage (on the Pi, where the HA container runs):
#     sudo ./docker/homeassistant/apply-dashboard.sh
#
# Overrides:
#     HA_URL=http://localhost:8123   HA_CONTAINER=homeassistant
#     HA_DASHBOARD_URL_PATH=icsee-camera
set -euo pipefail

REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
CONFIG="$REPO/docker/homeassistant/lovelace.icsee_camera.json"
HA_URL=${HA_URL:-http://localhost:8123}
CONTAINER=${HA_CONTAINER:-homeassistant}
URL_PATH=${HA_DASHBOARD_URL_PATH:-icsee-camera}
TITLE=${HA_DASHBOARD_TITLE:-Camera}
ICON=${HA_DASHBOARD_ICON:-mdi:cctv}

# shellcheck disable=SC1091
[ -f "$REPO/secrets" ] && . "$REPO/secrets"
: "${HA_USER:?set HA_USER in $REPO/secrets}"
: "${HA_PASS:?set HA_PASS in $REPO/secrets}"
[ -f "$CONFIG" ] || { echo "missing $CONFIG"; exit 1; }

DOCKER=docker
$DOCKER ps >/dev/null 2>&1 || DOCKER="sudo docker"
$DOCKER ps --format '{{.Names}}' | grep -qx "$CONTAINER" \
  || { echo "container '$CONTAINER' is not running"; exit 1; }

# The websockets client only exists inside the HA container, so the payload runs
# there. Copy the config where the container can read it, then pipe the rest.
$DOCKER cp "$CONFIG" "$CONTAINER:/tmp/lovelace.icsee_camera.json"

HA_URL="$HA_URL" HA_USER="$HA_USER" HA_PASS="$HA_PASS" \
URL_PATH="$URL_PATH" TITLE="$TITLE" ICON="$ICON" \
  $DOCKER exec -i -e HA_URL -e HA_USER -e HA_PASS -e URL_PATH -e TITLE -e ICON \
    "$CONTAINER" python3 - <<'PY'
import asyncio, json, os, urllib.parse, urllib.request

import websockets  # shipped with Home Assistant (verified: 15.0.1)

HA_URL   = os.environ["HA_URL"].rstrip("/")
USER     = os.environ["HA_USER"]
PASSWORD = os.environ["HA_PASS"]
URL_PATH = os.environ["URL_PATH"]
TITLE    = os.environ["TITLE"]
ICON     = os.environ["ICON"]
CONFIG   = "/tmp/lovelace.icsee_camera.json"
CLIENT_ID = HA_URL + "/"


def post_json(path, payload):
    req = urllib.request.Request(
        HA_URL + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.load(resp)


def post_form(path, payload):
    req = urllib.request.Request(
        HA_URL + path,
        data=urllib.parse.urlencode(payload).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.load(resp)


def login():
    """Username/password -> short-lived access token, no stored secret."""
    flow = post_json(
        "/auth/login_flow",
        {"client_id": CLIENT_ID, "handler": ["homeassistant", None],
         "redirect_uri": CLIENT_ID},
    )
    step = post_json(
        f"/auth/login_flow/{flow['flow_id']}",
        {"client_id": CLIENT_ID, "username": USER, "password": PASSWORD},
    )
    if step.get("type") != "create_entry":
        raise SystemExit(f"login failed: {step}")
    token = post_form(
        "/auth/token",
        {"grant_type": "authorization_code", "code": step["result"],
         "client_id": CLIENT_ID},
    )
    return token["access_token"]


async def main():
    config = json.load(open(CONFIG))
    token = login()
    async with websockets.connect(HA_URL.replace("http", "ws") + "/api/websocket",
                                  max_size=None) as ws:
        await ws.recv()
        await ws.send(json.dumps({"type": "auth", "access_token": token}))
        auth = json.loads(await ws.recv())
        if auth.get("type") != "auth_ok":
            raise SystemExit(f"auth failed: {auth}")

        async def call(msg_id, **msg):
            await ws.send(json.dumps({"id": msg_id, **msg}))
            while True:
                res = json.loads(await ws.recv())
                if res.get("id") == msg_id:
                    return res

        # Register the dashboard if it is not there yet, so a fresh HA gets it too.
        dash = await call(1, type="lovelace/dashboards/list")
        if not any(d.get("url_path") == URL_PATH for d in dash.get("result", [])):
            created = await call(
                2, type="lovelace/dashboards/create", url_path=URL_PATH,
                title=TITLE, icon=ICON, show_in_sidebar=True,
                require_admin=False, mode="storage",
            )
            if not created.get("success"):
                raise SystemExit(f"dashboard create failed: {created}")
            print(f"  created dashboard '{URL_PATH}'")
        else:
            print(f"  dashboard '{URL_PATH}' already registered")

        saved = await call(
            3, type="lovelace/config/save", url_path=URL_PATH, config=config,
        )
        if not saved.get("success"):
            raise SystemExit(f"config save failed: {saved}")
        views = ", ".join(v.get("title", "?") for v in config["views"])
        print(f"  saved {URL_PATH}: {len(config['views'])} view(s) [{views}]")


asyncio.run(main())
PY
