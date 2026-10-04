#!/bin/bash
# 48-hour burn-in probe for the migrated Armbian media stack (task 7.13).
# Read-only and safe to run at any time; needs only the `docker` group.
#   scripts/burnin-check.sh            # one snapshot, exit 1 on any problem
#   scripts/burnin-check.sh --log      # also append the snapshot to
#                                      # ~/docker-data/burnin.log
#   scripts/burnin-check.sh --baseline # write ~/burnin-baseline (restart counts)
# A "restart count grew" delta is reported only when a baseline exists.
set -u

SERVICES="gluetun qbittorrent jackett stremio"
BASE="$HOME/burnin-baseline"
LOG="$HOME/docker-data/burnin.log"
FAIL=0

emit(){ printf '%s\n' "$*"; }
ok(){  printf '  ok    %-24s %s\n' "$1" "$2"; }
bad(){ printf '  FAIL  %-24s %s\n' "$1" "$2"; FAIL=1; }

snapshot(){
  emit "== burn-in $(date -u +%FT%TZ)  (up: $(uptime -p | sed 's/^up //')) =="

  # --- containers: state, health, restart count delta vs baseline -------
  for c in $SERVICES; do
    info=$(docker inspect -f \
      '{{.RestartCount}} {{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}-{{end}}' \
      "$c" 2>/dev/null) || { bad "$c" "not found"; continue; }
    read -r rc st hl <<<"$info"
    if [ "$st" != "running" ] || { [ "$hl" != "-" ] && [ "$hl" != "healthy" ]; }; then
      bad "$c" "status=$st health=$hl restarts=$rc"
    elif [ -f "$BASE" ]; then
      brc=$(awk -v n="$c" '$1==n{print $2}' "$BASE")
      if [ -n "$brc" ] && [ "$rc" -gt "$brc" ] 2>/dev/null; then
        bad "$c" "restarted during burn-in ($brc -> $rc)"
      else
        ok "$c" "running health=$hl restarts=$rc"
      fi
    else
      ok "$c" "running health=$hl restarts=$rc"
    fi
  done

  # --- VPN: the container can be "Up" while the tunnel talks to nobody ----
  ip=$(docker exec qbittorrent curl -s --max-time 10 https://ipinfo.io/ip 2>/dev/null | tr -d '\r\n')
  case "$ip" in
    45.89.249.*) ok "vpn egress" "$ip (PIA Toronto)" ;;
    "")          bad "vpn egress" "no answer - tunnel or DNS down" ;;
    *)           bad "vpn egress" "$ip - expected 45.89.249.x (PIA)" ;;
  esac

  # --- Web UIs ----------------------------------------------------------
  for p in 8080:qbittorrent 9117:jackett; do
    port=${p%%:*}; name=${p##*:}
    code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 8 "http://127.0.0.1:$port/" 2>/dev/null)
    case "$code" in
      200|301|302) ok "$name web" "HTTP $code" ;;
      *)           bad "$name web" "HTTP ${code:-none} on :$port" ;;
    esac
  done

  # --- host capacity ----------------------------------------------------
  use=$(df --output=pcent / | tail -1 | tr -dc 0-9)
  avail=$(df -h --output=avail / | tail -1 | tr -d ' ')
  if [ -z "$use" ] || [ "$use" -ge 90 ]; then bad "root disk" "${use:-unknown}% used (${avail} free)"; else ok "root disk" "$use% used (${avail} free)"; fi

  mav=$(free -m | awk '/^Mem:/{print $7}')
  if [ "$mav" -lt 300 ]; then bad "memory" "${mav} MiB available"; else ok "memory" "${mav} MiB available"; fi

  emit ""
}

if [ "${1:-}" = "--baseline" ]; then
  : > "$BASE"
  for c in $SERVICES; do
    printf '%s %s\n' "$c" \
      "$(docker inspect -f '{{.RestartCount}}' "$c" 2>/dev/null || echo 0)" >> "$BASE"
  done
  emit "baseline written to $BASE:"; cat "$BASE"
  exit 0
fi

out=$(snapshot)
emit "$out"
if [ "${1:-}" = "--log" ]; then
  mkdir -p "$(dirname "$LOG")"
  { printf '%s\n' "$out"; [ "$FAIL" -ne 0 ] && emit "  ^^ PROBLEM"; } >> "$LOG"
fi
exit "$FAIL"
