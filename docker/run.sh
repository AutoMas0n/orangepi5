#!/bin/bash
# Idempotent script to manage the media stack.
#
# 2026-09-30: rewritten. The old version depended on the current directory and
# on a `cd gluetun` side effect (which only happened when pia-wg-config was
# missing) for its ../.. paths to resolve - that is how service configs ended up
# under /root instead of /home/orangepi. It also generated a WireGuard config via
# pia-wg-config, which PIA's API can no longer support (addKey returns 404).
# gluetun now uses its native PIA provider, so no config file is generated here.
# All paths below are absolute; no HOME or CWD dependence.
set -uo pipefail

REPO=/home/orangepi/Github/orangepi5
DOCKER_DIR="$REPO/docker"

remove_docker_container() {
  local container_name=$1
  if sudo docker ps -q -f name=^/${container_name}$; then sudo docker stop "$container_name"; fi
  if sudo docker ps -aq -f name=^/${container_name}$; then sudo docker rm -f "$container_name"; fi
}

restart_docker_compose() {
  local dir=$1 service=$2
  if [ -f "$dir/docker-compose.yml" ]; then
    ( cd "$dir" && sudo docker-compose rm -sf "$service" >/dev/null 2>&1; sudo docker-compose up -d "$service" )
  else
    echo "docker-compose.yml not found in $dir"
  fi
}

remove_docker_container gluetun
restart_docker_compose "$DOCKER_DIR/qbittorrent" qbittorrent
restart_docker_compose "$DOCKER_DIR/qbittorrent" jackett
restart_docker_compose "$DOCKER_DIR/qbittorrent" stremio
restart_docker_compose "$DOCKER_DIR/homeassistant" homeassistant
