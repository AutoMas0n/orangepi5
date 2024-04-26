#!/bin/bash
# Idempotent script to manage PIA, qBittorrent, and Jellyfin

# Function to check if a command exists
command_exists() {
  type "$1" &>/dev/null
}

# Function to stop and remove a Docker container by name
remove_docker_container() {
  local container_name=$1
  # Check if container is running and stop it
  if sudo docker ps -q -f name=^/${container_name}$; then
    sudo docker stop "$container_name"
  fi
  # Check if container exists (running or not) and remove it
  if sudo docker ps -aq -f name=^/${container_name}$; then
    sudo docker rm -f "$container_name"
  fi
}

# Function to restart Docker Compose service if it's already running
restart_docker_compose() {
  local dir=$1
  local service=$2
  if [ -f "$dir/docker-compose.yml" ]; then
    cd "$dir" || exit
    # Stop and remove a specific service if it's running
    if sudo docker-compose ps -q "$service" | grep -q '.'; then
      sudo docker-compose rm -sf "$service"
    fi
    # Start the service
    sudo docker-compose up -d "$service"
  else
    echo "docker-compose.yml not found in $dir"
  fi
}

# Install pia-wg-config if not already installed
if ! command_exists pia-wg-config; then
  cd gluetun || exit
  source /etc/profile && export PATH=$PATH:$(go env GOPATH)/bin
  go install github.com/kylegrantlucas/pia-wg-config@latest
fi

# Load PIA credentials and generate config if it doesn't exist or if credentials changed
PIA_CREDENTIALS_FILE=../../secrets
if [ -f "$PIA_CREDENTIALS_FILE" ]; then
  source "$PIA_CREDENTIALS_FILE"
  WG_CONFIG_FILE=../../wg0.conf
  # Check if config exists and if PIA credentials have changed
  if [ ! -f "$WG_CONFIG_FILE" ] || ! grep -q "$PIA_USER" "$WG_CONFIG_FILE"; then
    pia-wg-config -o "$WG_CONFIG_FILE" -r "ca_toronto" "$PIA_USER" "$PIA_PASS"
  fi
else
  echo "PIA credentials file not found at $PIA_CREDENTIALS_FILE"
  exit 1
fi


# Stop and remove the gluetun container if it exists
remove_docker_container gluetun
# Restart qBittorrent if it's already running
restart_docker_compose ../qbittorrent qbittorrent
restart_docker_compose ../qbittorrent jackett
# Restart Jellyfin if it's already running
restart_docker_compose ../jellyfin jellyfin