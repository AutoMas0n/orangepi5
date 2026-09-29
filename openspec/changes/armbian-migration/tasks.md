> **📋 Human companion file**: Before starting, give the human `openspec/changes/armbian-migration/HUMAN.md` — it tells them exactly when to plug in drives, boot from SD, etc. The tasks below reference 👤 sections that need human physical action.

> **⚠️ Known trap**: `docker/run.sh` has a latent relative-path bug — the `PIA_CREDENTIALS_FILE=../../secrets` and `restart_docker_compose ../qbittorrent` paths resolve inconsistently depending on whether `pia-wg-config` is already installed. If the script errors on auth but containers still start (because the existing `wg0.conf` is valid), the VPN is actually working. Do not waste time debugging — the auth failure is a separate PIA credentials issue noted in task 9.1.

## 1. Preparation (on current Ubuntu)

- [x] 1.1 Clean up remaining waste: empty trash, clear browser caches, remove duplicate Go in /root
- [x] 1.2 Verify all Docker containers are healthy and running (jellyfin, qbittorrent, jackett, stremio, gluetun, copyparty)
- [x] 1.3 Verify wg0.conf exists and contains valid WireGuard keys (`/home/orangepi/Github/orangepi5/wg0.conf`)
- [x] 1.4 Commit and push the migration branch: `git push origin migration/armbian`
- [x] 1.5 Disable cron jobs that could write data during backup (`crontab -l`, note them for restore)
- [x] 1.6 Note current network config (`ip addr`, `ip route`, `resolvectl`) for static IP on Armbian
- [x] 1.7 List currently installed packages for the convenience layer (`dpkg --get-selections > ~/packages.txt`)
## 2. Backup

> **👤 Human required**: Plug in the external NVMe via USB-C (2.1). Everything else the agent can run over SSH.

> **⚠️ Nesting trap**: The backup NVMe auto-mounts under `/media/`. If you rsync `/media/` directly to a path on the same drive, it copies the backup into itself — filling the drive with infinite nesting. **Always bind-mount the NVMe at `/mnt/backup-nvme` first** to keep source and destination paths separate.

- [x] 2.1 Connect external NVMe via USB-C, run `lsblk` to find its mount point (typically `/media/orangepi/WavLink`)
- [x] 2.2 Bind-mount at `/mnt/backup-nvme` and create backup directory:
     ```bash
     sudo mkdir -p /mnt/backup-nvme
     sudo mount --bind /media/orangepi/WavLink /mnt/backup-nvme
     sudo mkdir -p /mnt/backup-nvme/armbian-migration-backup
     ```
- [x] 2.3 Back up gitignored secret files explicitly (belt-and-suspenders — also captured by rsync in 2.4):
     ```bash
     cp ~/Github/orangepi5/secrets /mnt/backup-nvme/armbian-migration-backup/secrets.backup
     cp ~/Github/orangepi5/wg0.conf /mnt/backup-nvme/armbian-migration-backup/wg0.conf.backup
     ```
- [x] 2.4 Rsync /home/orangepi to backup NVMe (`rsync -aAXv --info=progress2 /home/orangepi/ /mnt/backup-nvme/armbian-migration-backup/home-backup/`)
- [x] 2.5 Verify /home backup integrity (`diff -r --brief /home/orangepi/ /mnt/backup-nvme/armbian-migration-backup/home-backup/ | grep -v "^Only in"` or file count comparison)
- [x] 2.6 Rsync /media to backup NVMe (`rsync -aAXv --info=progress2 /media/ /mnt/backup-nvme/armbian-migration-backup/media-backup/`)
- [x] 2.7 Verify /media backup integrity (file count comparison):
     ```bash
     echo "Source: $(sudo find /media/ -type f | wc -l) files"
     echo "Dest:   $(sudo find /mnt/backup-nvme/armbian-migration-backup/media-backup/ -type f | wc -l) files"
     ```
- [x] 2.8 Make a note of which running containers need their images saved vs re-pulled (`sudo docker ps`)

## 3. Download Armbian and Prepare Flash Medium

> **👤 Human required**: Tasks 3.3–3.8 require physical access to the Orange Pi 5.
> The agent can download the image and verify it, but writing to SD, booting, and power-cycling are physical actions.
> For the flash itself (3.6–3.7), boot from the SD, then the agent can SSH in and run the  and  commands from the live environment.

- [ ] 3.1 Download the Armbian Trixie current minimal image: `wget https://dl.armbian.com/orangepi5/Trixie_current_minimal -O ~/Downloads/Armbian_Trixie_orangepi5.img.xz` or download via browser
- [ ] 3.2 Verify the download checksum (compare SHA256 against the image page)
- [ ] 3.3 Write Armbian image to an SD card or USB stick for initial boot (following existing `flash-image-ansible/` process, substituting Armbian image)
- [ ] 3.4 Copy rkspi_loader.img and Armbian image to the flash medium
- [ ] 3.5 Boot from SD/USB flash medium
- [ ] 3.6 Delete all partitions on NVMe:
     ```bash
     echo -e "p\nd\n1\nd\n2\nd\nd\nw\nY\nY" | sudo gdisk /dev/mtdblock0
     echo -e "p\nd\n1\nd\n2\nd\nd\nw\nY\nY" | sudo gdisk /dev/nvme0n1
     ```
- [ ] 3.7 Flash bootloader firmware, then write Armbian image:
     ```bash
     sudo dd if=/path/to/rkspi_loader.img of=/dev/mtdblock0 conv=notrunc
     sudo xzcat /path/to/Armbian_*_Orangepi5_trixie_current_*.img.xz | sudo dd bs=1M of=/dev/nvme0n1 status=progress
     ```
- [ ] 3.8 Shut down, remove flash medium, power on from NVMe

## 4. First Boot & Armbian Setup

> **👤 Human required**: The first-boot wizard (4.1) runs on the console — plug in a monitor+keyboard or use the Armbian serial console.
> Task 4.3 onwards can be done remotely once networking is up and credentials are set.

- [ ] 4.1 Complete Armbian first-boot wizard: set hostname (orangepi), create user (orangepi), set password, configure timezone
- [ ] 4.2 Configure static IP to 192.168.2.113:
     ```bash
     sudo nmcli con mod eth0 ipv4.addresses 192.168.2.113/24
     sudo nmcli con mod eth0 ipv4.gateway 192.168.2.1
     sudo nmcli con mod eth0 ipv4.dns 8.8.8.8
     sudo nmcli con mod eth0 ipv4.method manual
     sudo nmcli con down eth0 && sudo nmcli con up eth0
     ```
- [ ] 4.3 Verify SSH access is working from the network
- [ ] 4.4 Run `apt update && apt upgrade -y` to bring system current

## 5. Core Services Setup

- [ ] 5.1 Install Docker and docker-compose-plugin (`apt install docker.io docker-compose-plugin -y`)
- [ ] 5.2 Add orangepi user to docker group (`sudo usermod -aG docker orangepi`)
- [ ] 5.3 Verify Docker works without sudo (`docker ps`)
- [ ] 5.4 Clone the repo (SSH — keys restored from `/home` backup):
     ```bash
     git clone git@github.com:AutoMas0n/orangepi5.git ~/Github/orangepi5
     cd ~/Github/orangepi5 && git checkout migration/armbian
     ```
- [ ] 5.5 Restore /home/orangepi from backup NVMe: `rsync -aAXv /mnt/backup-nvme/armbian-migration-backup/home-backup/ /home/orangepi/`
- [ ] 5.6 Restore gitignored secret files from backup:
     ```bash
     cp /mnt/backup-nvme/armbian-migration-backup/secrets.backup ~/Github/orangepi5/secrets
     cp /mnt/backup-nvme/armbian-migration-backup/wg0.conf.backup ~/Github/orangepi5/wg0.conf
     ```
- [ ] 5.7 Verify SSH key is present for git: `ls -la ~/.ssh/id_ed25519` (should exist if backed up from /home)
- [ ] 5.8 Verify Documents/ directory structure matches expected Docker bind mounts (`~/Documents/jellyfin`, `~/Documents/qbittorrent`, `~/Documents/jackett`)

## 6. Docker Stack Deployment

- [ ] 6.1 Pull all 6 Docker images:
     ```bash
     sudo docker pull qmcgaw/gluetun
     sudo docker pull lscr.io/linuxserver/jackett
     sudo docker pull lscr.io/linuxserver/qbittorrent
     sudo docker pull lscr.io/linuxserver/jellyfin
     sudo docker pull stremio/server
     sudo docker pull copyparty/ac
     ```
- [ ] 6.2 Restore /media from backup NVMe (`rsync -aAXv /mnt/backup-nvme/armbian-migration-backup/media-backup/ /media/`)
- [ ] 6.3 Run the Docker stack: `cd ~/Github/orangepi5 && sudo ./docker/run.sh`
- [ ] 6.4 Verify each container is running and healthy (`docker ps --format "table {{.Names}} {{.Status}}"`)
- [ ] 6.5 Test Jellyfin at http://192.168.2.113:8096
- [ ] 6.6 Test qBittorrent WebUI at http://192.168.2.113:8080
- [ ] 6.7 Verify Gluetun VPN connection is active (check container logs for WireGuard handshake)

## 7. Verification & Validation

Run each check against the Baseline in `design.md`.

- [ ] 7.1 Network: verify IP is 192.168.2.113/24, gateway 192.168.2.1, DNS 8.8.8.8 (`ip addr`, `ip route`, `resolvectl`)
- [ ] 7.2 MAC address matches baseline: 0a:79:72:f3:0f:3b (`ip addr show eth0`)
- [ ] 7.3 All 5 Docker services are running and healthy (`sudo docker ps --format "table {{.Names}} {{.Status}}"`)
- [ ] 7.4 Gluetun shows "healthy" status (`sudo docker ps --filter name=gluetun`)
- [ ] 7.5 Gluetun VPN is connected (check public IP matches PIA Toronto region in container logs)
- [ ] 7.6 Jellyfin responds at http://192.168.2.113:8096 (curl or browser)
- [ ] 7.7 qBittorrent WebUI responds at http://192.168.2.113:8080
- [ ] 7.8 Jackett responds at http://192.168.2.113:9117
- [ ] 7.9 All 6 container images match the baseline list (`sudo docker image ls`)
- [ ] 7.10 Cron jobs restored correctly: user and root crontab match baseline
- [ ] 7.11 Storage layout matches: single partition, /boot/firmware mounted, no RAID warnings
- [ ] 7.12 Set up cron jobs for daily docker pull and watchtower (from `docker/README.md`)
- [ ] 7.13 Run 48-hour burn-in check before declaring rollback window closed

## 8. Finalization (after 48-hour burn-in passes)

- [ ] 8.1 On the new Armbian system, ensure the migration branch is up to date: `cd ~/Github/orangepi5 && git pull origin migration/armbian`
- [ ] 8.2 Push any post-migration fixes or config updates back to the branch
- [ ] 8.3 Merge migration/armbian into main and push: `git checkout main && git merge migration/armbian && git push origin main`
- [ ] 8.4 Delete the remote branch: `git push origin --delete migration/armbian`
- [ ] 8.5 Delete the local branch: `git branch -d migration/armbian`
- [ ] 8.6 Run `openspec archive change armbian-migration` to archive the completed change

## 9. Post-Migration Cleanup (deferred / optional)

- [ ] 9.1 Fix PIA credentials: debug `pia-wg-config` auth failure so `wg0.conf` can be regenerated. Verify with `sudo ./docker/run.sh`
- [ ] 9.2 Install Docker auto-prune cron: `docker system prune --volumes -f` weekly to prevent image/volume bloat
- [ ] 9.3 Install convenience extras as needed (VS Code, RustDesk, Firefox, Go, Flatpak apps) — one at a time
- [ ] 9.4 Add Copyparty to docker-compose stack. From inspection: runs on port 3923, mounts `/media` read-only+copy. Add a compose service block like:
     ```yaml
     copyparty:
       image: copyparty/ac:latest
       container_name: copyparty
       command: --http-only -v /media:media:r:c,e2d,e2t
       ports:
         - 3923:3923
       volumes:
         - /media:/media:ro
       restart: unless-stopped
     ```
     Place in `docker/copyparty/docker-compose.yml` or the main stack file, then `sudo docker compose up -d copyparty`
- [ ] 9.5 Clean up old backup drives