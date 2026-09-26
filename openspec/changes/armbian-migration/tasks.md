## 1. Preparation (on current Ubuntu)

- [ ] 1.1 Clean up remaining waste: empty trash, clear browser caches, remove duplicate Go in /root
- [ ] 1.2 Verify all Docker containers are healthy and running (jellyfin, qbittorrent, jackett, stremio, gluetun, copyparty)
- [ ] 1.3 Verify wg0.conf exists and contains valid WireGuard keys (`/home/orangepi/Github/orangepi5/wg0.conf`)
- [ ] 1.4 Commit and push the migration branch: `git push origin migration/armbian`
- [ ] 1.5 Disable cron jobs that could write data during backup (`crontab -l`, note them for restore)
- [ ] 1.6 Note current network config (`ip addr`, `ip route`, `resolvectl`) for static IP on Armbian
- [ ] 1.7 List currently installed packages for the convenience layer (`dpkg --get-selections > ~/packages.txt`)

## 2. Backup

- [ ] 2.1 Connect backup drive and verify it's mounted (`/mnt/backup-drive/`)
- [ ] 2.2 Rsync /home/orangepi to backup drive (`rsync -aAXv --info=progress2 /home/orangepi/ /mnt/backup-drive/home-backup/`)
- [ ] 2.3 Verify /home backup integrity (`diff -r --brief /home/orangepi/ /mnt/backup-drive/home-backup/ | grep -v "^Only in"` or file count comparison)
- [ ] 2.4 Rsync /media to temporary storage (`rsync -aAXv --info=progress2 /media/ /mnt/temp-media-store/media-backup/`)
- [ ] 2.5 Verify /media backup integrity
- [ ] 2.6 Make a note of which running containers need their images saved vs re-pulled (`docker image ls`)

## 3. Download Armbian and Prepare Flash Medium

- [ ] 3.1 Download the Armbian Trixie current minimal image: `wget https://dl.armbian.com/orangepi5/Trixie_current_minimal -O ~/Downloads/Armbian_Trixie_orangepi5.img.xz` or download via browser
- [ ] 3.2 Verify the download checksum (compare SHA256 against the image page)
- [ ] 3.3 Write Armbian image to an SD card or USB stick for initial boot (following existing `flash-image-ansible/` process, substituting Armbian image)
- [ ] 3.4 Copy rkspi_loader.img and Armbian image to the flash medium
- [ ] 3.5 Boot from SD/USB, wipe NVMe partitions, flash rkspi_loader to /dev/mtdblock0, dd Armbian image to /dev/nvme0n1
- [ ] 3.6 Shut down, remove flash medium, power on from NVMe

## 4. First Boot & Armbian Setup

- [ ] 4.1 Complete Armbian first-boot wizard: set hostname (orangepi), create user (orangepi), set password, configure timezone
- [ ] 4.2 Configure static IP to 192.168.2.113 via armbian-config or nmcli
- [ ] 4.3 Verify SSH access is working from the network
- [ ] 4.4 Run `apt update && apt upgrade -y` to bring system current

## 5. Core Services Setup

- [ ] 5.1 Install Docker and docker-compose-plugin (`apt install docker.io docker-compose-plugin -y`)
- [ ] 5.2 Add orangepi user to docker group (`sudo usermod -aG docker orangepi`)
- [ ] 5.3 Verify Docker works without sudo (`docker ps`)
- [ ] 5.4 Clone the repo: `git clone https://github.com/automationStati0n/orangepi5 ~/Github/orangepi5`
- [ ] 5.5 Restore /home/orangepi from backup drive: `rsync -aAXv /mnt/backup-drive/home-backup/ /home/orangepi/`
- [ ] 5.6 Verify Documents/ directory structure matches expected Docker bind mounts (`~/Documents/jellyfin`, `~/Documents/qbittorrent`, `~/Documents/jackett`)

## 6. Docker Stack Deployment

- [ ] 6.1 Pull latest Docker images: `sudo docker pull qmcgaw/gluetun lscr.io/linuxserver/jackett lscr.io/linuxserver/qbittorrent lscr.io/linuxserver/jellyfin stremio/server`
- [ ] 6.2 Restore /media from temporary storage (`rsync -aAXv /mnt/temp-media-store/media-backup/ /media/`)
- [ ] 6.3 Run the Docker stack: `cd ~/Github/orangepi5 && sudo ./docker/run.sh`
- [ ] 6.4 Verify each container is running and healthy (`docker ps --format "table {{.Names}} {{.Status}}"`)
- [ ] 6.5 Test Jellyfin at http://192.168.2.113:8096
- [ ] 6.6 Test qBittorrent WebUI at http://192.168.2.113:8080
- [ ] 6.7 Verify Gluetun VPN connection is active (check container logs for WireGuard handshake)

## 7. Verification & Validation

- [ ] 7.1 Confirm all services work identically to the previous setup
- [ ] 7.2 Set up cron jobs for daily docker pull and watchtower (from `docker/README.md`)
- [ ] 7.3 Run 48-hour burn-in check before declaring rollback window closed

## 8. Finalization (after 48-hour burn-in passes)

- [ ] 8.1 On the new Armbian system: `cd ~/Github/orangepi5 && git checkout -b migration/armbian origin/migration/armbian` to pull the latest branch
- [ ] 8.2 Push any post-migration fixes or config updates back to the branch
- [ ] 8.3 Merge migration/armbian into main and push: `git checkout main && git merge migration/armbian && git push origin main`
- [ ] 8.4 Delete the remote branch: `git push origin --delete migration/armbian`
- [ ] 8.5 Delete the local branch: `git branch -d migration/armbian`
- [ ] 8.6 Run `openspec archive change armbian-migration` to archive the completed change

## 9. Post-Migration Cleanup (deferred / optional)

- [ ] 9.1 Fix PIA credentials: debug `pia-wg-config` auth failure so `wg0.conf` can be regenerated. Verify with `sudo ./docker/run.sh`
- [ ] 9.2 Install Docker auto-prune cron: `docker system prune --volumes -f` weekly to prevent image/volume bloat
- [ ] 9.3 Install convenience extras as needed (VS Code, RustDesk, Firefox, Go, Flatpak apps) — one at a time
- [ ] 9.4 Add the undocumented Copyparty container to the repo's docker-compose stack
- [ ] 9.5 Clean up old backup drives