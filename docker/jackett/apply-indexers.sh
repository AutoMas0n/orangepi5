#!/bin/bash
# (Re)configure Jackett's TorrentLeech indexer from secrets, via its own API.
#
# Discovered the hard way, so it is written down here: Jackett's admin API is
# session-based (fetch /UI/Login with a cookie jar first), and the config payload
# is an ARRAY OF {id, value} items - not {name,...} - because
# ConfigurationData.LoadConfigDataValuesFromJson matches on "id":
#     jsonArray.FirstOrDefault(f => f.Value<string>("id") == item.ID)
# Jackett also *validates the login while saving*, so wrong credentials give
# HTTP 500 and nothing is persisted. A correct save returns 204.
#
# Usage: sudo ./docker/jackett/apply-indexers.sh
set -euo pipefail
REPO=/home/orangepi/Github/orangepi5
JACKETT=${JACKETT_URL:-http://192.168.2.113:9117}
SECRETS="$REPO/secrets"
CJ=$(mktemp); trap 'rm -f "$CJ"' EXIT
[ -f "$SECRETS" ] || { echo "missing $SECRETS"; exit 1; }

curl -sL -c "$CJ" -b "$CJ" -o /dev/null --max-time 20 "$JACKETT/UI/Login"

python3 - "$SECRETS" <<'PY'
import json, sys
cfg = dict(l.strip().split("=", 1) for l in open(sys.argv[1]) if "=" in l)
if not cfg.get("TL_USER"):
    sys.exit("TL_USER not set in secrets")
items = [("username", cfg["TL_USER"]), ("password", cfg["TL_PASS"]), ("alt2fatoken", ""),
         ("freeleech", "false"), ("exclude_scene", "false"), ("exclude_archives", "false")]
json.dump([{"id": i, "value": v} for i, v in items], open("/tmp/jackett-tl.json", "w"))
PY

code=$(curl -s -b "$CJ" -o /tmp/jackett-tl.out -w '%{http_code}' --max-time 90 -X POST \
  -H 'Content-Type: application/json' --data @/tmp/jackett-tl.json \
  "$JACKETT/api/v2.0/indexers/torrentleech/config")
[ "$code" = "204" ] || { echo "config rejected (HTTP $code):"; head -c 200 /tmp/jackett-tl.out; exit 1; }
echo "  TorrentLeech indexer configured (HTTP 204)"

KEY=$(python3 -c "import json;print(json.load(open('$REPO/docker/../docker-data/Jackett/ServerConfig.json'))['APIKey'])" 2>/dev/null || echo "")
[ -n "$KEY" ] && echo "  verifying with a search:" && \
  curl -s --max-time 120 "$JACKETT/api/v2.0/indexers/torrentleech/results/torznab/api?apikey=$KEY&t=search&q=matrix" \
  | grep -c '<item>' | sed 's/^/    results: /'
