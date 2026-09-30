#!/bin/bash

# Define the images to pull
images=(
  "qmcgaw/gluetun"
  "lscr.io/linuxserver/jackett"
  "lscr.io/linuxserver/qbittorrent"
  "stremio/server"
  "copyparty/ac"
  # Add or remove images as needed
)

# Function to pull images
pull_images() {
  for image in "${images[@]}"; do
    echo "Pulling image: $image"
    sudo docker pull "$image"
  done
}

# Schedule the script to run daily using cron
schedule_cron_job() {
  script_path="$(realpath "$0")"
  cron_job="0 0 * * * $script_path"
  
  # Remove any existing cron job for this script
  (crontab -l 2>/dev/null | grep -vF "$script_path") | crontab -
  
  # Add the new cron job
  (crontab -l 2>/dev/null; echo "$cron_job") | crontab -
}

# Main script
pull_images
schedule_cron_job
