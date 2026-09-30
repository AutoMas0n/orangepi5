#!/bin/bash
# Re-apply qBittorrent's tuned preferences through its own WebUI API.
# Idempotent and version-proof: these keys are the API's, so this does not break
# when qBittorrent renames an internal qBittorrent.conf key. The *state* file is
# deliberately not in git; only this.
# Usage: QBIT_USER=admin QBIT_PASS=admin ./apply-preferences.sh
set -euo pipefail
HOST=${QBIT_HOST:-192.168.2.113:8080}
USER=${QBIT_USER:-admin}
PASS=${QBIT_PASS:-admin}
CJ=$(mktemp); trap 'rm -f "$CJ"' EXIT
code=$(curl -s -c "$CJ" -o /dev/null -w '%{http_code}' --max-time 15 \
  -d "username=$USER&password=$PASS" "http://$HOST/api/v2/auth/login")
[ "$code" = "204" ] || { echo "login failed (HTTP $code)"; exit 1; }
cat > /tmp/qb-prefs.json <<'JSON'
{
 "save_path": "/downloads/",
 "temp_path_enabled": true,
 "temp_path": "/downloads/incomplete",
 "preallocation": true,
 "disk_cache": -1,
 "async_io_threads": 4,
 "max_connec": 500,
 "max_connec_per_torrent": 100,
 "max_uploads": 20,
 "max_uploads_per_torrent": 10,
 "queueing_enabled": true,
 "max_active_downloads": 5,
 "max_active_uploads": 5,
 "max_active_torrents": 10,
 "dht": false,
 "pex": false,
 "lsd": false,
 "encryption": 1,
 "anonymous_mode": false,
 "upnp": false,
 "dl_limit": 0,
 "up_limit": 0,
 "bittorrent_protocol": 0,
 "listen_port": 6881,
 "use_random_port": false,
 "save_resume_data_interval": 60,
 "max_ratio_enabled": false,
 "max_seeding_time_enabled": false,
 "rss_processing_enabled": true,
 "rss_auto_downloading_enabled": true,
 "web_ui_port": 8080,
 "web_ui_username": "admin",
 "web_ui_csrf_protection": true,
 "web_ui_host_header_validation": false,
 "web_ui_clickjacking_protection": true
}
JSON
curl -s -b "$CJ" -o /dev/null -w '  setPreferences HTTP %{http_code}\n' --max-time 20 \
  --data-urlencode "json@/tmp/qb-prefs.json" "http://$HOST/api/v2/app/setPreferences"
