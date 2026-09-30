#!/bin/bash
# Regenerate gluetun's wg0.conf using PIA's CURRENT WireGuard provisioning flow.
#
# Why this exists: pia-wg-config (and every other tool that POSTs to
# privateinternetaccess.com/api/client/v2/addKey) broke when PIA moved key
# registration to the VPN server itself:
#   1. POST https://www.privateinternetaccess.com/api/client/v2/token   (form: username, password)
#   2. read the region's wg server from https://serverlist.piaservers.net/vpninfo/servers/v6
#   3. GET  https://<wg-hostname>:1337/addKey?pt=<token>&pubkey=<pubkey>  (TLS verified against ca.rsa.4096.crt)
# PIA's own manual-connections repo implements exactly that, so this wraps it.
#
# Usage:  sudo ./docker/refresh-wireguard.sh [region_id]     (default: ca_toronto)
# Rotate the region if a tunnel stops handshaking (eg. ca_montreal, us_new_york).
set -euo pipefail
REGION="${1:-ca_toronto}"
REPO=/home/orangepi/Github/orangepi5
WORK=/opt/pia-manual-connections
SECRETS="$REPO/secrets"

[ -f "$SECRETS" ] || { echo "missing $SECRETS (needs PIA_USER/PIA_PASS)"; exit 1; }
. "$SECRETS"
command -v jq >/dev/null || { apt-get update -qq && apt-get install -y jq; }
command -v wg >/dev/null || { apt-get update -qq && apt-get install -y wireguard-tools; }

if [ -d "$WORK/.git" ]; then git -C "$WORK" pull -q --ff-only || true
else git clone -q --depth 1 https://github.com/pia-foss/manual-connections "$WORK"; fi
cd "$WORK"
mkdir -p /opt/piavpn-manual

echo "==> requesting token"
out=$(PIA_USER="$PIA_USER" PIA_PASS="$PIA_PASS" ./get_token.sh 2>&1 | sed 's/\x1b\[[0-9;]*[a-zA-Z]//g')
TOKEN=$(printf '%s\n' "$out" | sed -n 's/^PIA_TOKEN=//p' | head -1)
[ -n "$TOKEN" ] || { echo "token request failed:"; printf '%s\n' "$out" | tail -5; exit 1; }

echo "==> selecting a wireguard server in $REGION"
read -r IP CN <<<"$(curl -s --max-time 20 https://serverlist.piaservers.net/vpninfo/servers/v6 | head -1 \
  | jq -r --arg R "$REGION" '.regions[] | select(.id==$R) | .servers.wg[0] | "\(.ip) \(.cn)"')"
[ -n "${IP:-}" ] || { echo "no wireguard server for region $REGION"; exit 1; }
echo "    $CN ($IP)"

echo "==> registering the key and writing the config (host routing untouched)"
PIA_CONNECT=false PIA_CONF_PATH=/root/pia-wg.conf PIA_TOKEN="$TOKEN" \
  WG_SERVER_IP="$IP" WG_HOSTNAME="$CN" ./connect_to_wireguard_with_token.sh

install -d -m 700 "$REPO/wg0.backups" 2>/dev/null || true
[ -f "$REPO/wg0.conf" ] && cp -p "$REPO/wg0.conf" "$REPO/wg0.backups/wg0.conf.$(date +%s)"
install -m 600 /root/pia-wg.conf "$REPO/wg0.conf"
echo "==> installed $REPO/wg0.conf"
grep -iE '^Address|^Endpoint' "$REPO/wg0.conf"

echo "==> restarting the stack"
( cd "$REPO/docker" && ./run.sh >/dev/null 2>&1 )
sleep 45
echo "gluetun health: $(docker inspect gluetun --format '{{.State.Health.Status}}')"
docker logs gluetun 2>&1 | grep -i 'Public IP address' | tail -1
