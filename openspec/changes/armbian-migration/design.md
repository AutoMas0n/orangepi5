## Context

The Orange Pi 5 runs Ubuntu 22.04 on a 939 GB NVMe (currently ~165 GB used after Docker cleanup). The full media stack runs in Docker containers with configs in bind mounts (`~/Documents/`). `/media` holds ~133 GB of torrent/media files. A BTRFS RAID1 array across two USB drives exists but is normally powered off.

See proposal.md for the full motivation and scope.

## Goals / Non-Goals

**Goals:**
- Replace Ubuntu 22.04 with Armbian with zero service disruption after migration
- Preserve all Docker service configs (Jellyfin, qBittorrent, Jackett, Gluetun, Stremio, Copyparty)
- Preserve `/media` content (torrents, media files)
- Preserve static IP and network configuration
- Replace unreliable Ansible provisioning with a reliable, documented recovery procedure
- Keep the existing repo (`orangepi5`) as the single source of truth for the Docker stack

**Non-Goals:**
- Changing service behavior, ports, or capabilities
- Modifying the Docker compose files or service configuration
- Automating the entire process (some manual steps are acceptable for reliability)
- Changing the BTRFS RAID1 storage setup or mount points

## Decisions

### 1. Armbian Image Selection

**Decision:** Use the Armbian 26.8.1 Trixie (Debian 13 stable) current minimal image for Orange Pi 5.
- Download: `https://dl.armbian.com/orangepi5/Trixie_current_minimal` → resolves to `Armbian_26.8.1_Orangepi5_trixie_current_6.18.43_minimal.img.xz`
- Kernel: 6.18.43-rockchip

**Rationale:** Trixie is the current Debian stable release by late 2026. Armbian 26.8.1 provides an optimized rockchip kernel (6.18) with RK3588 hardware acceleration for Jellyfin GPU transcoding. The minimal variant keeps the install lean for a headless server. Debian base retains apt compatibility.

**Alternatives considered:**
- DietPi: Less hardware-optimized for Orange Pi 5, smaller community.
- Manual Debian install: No rockchip kernel optimizations, requires manual kernel management.
- Bookworm (Debian 12): Older kernel; lacks latest RK3588 hardware support improvements.

### 2. Provisioning Strategy (Ansible Replacement)

**Decision:** Two-tier approach:
1. **Critical path** (10-minute documented shell script sequence): Install Docker, configure network, mount storage, clone repo, pull images, run Docker stack. This is the only part needed for the server to be fully operational.
2. **Convenience extras** (manual or on-demand): VS Code, RustDesk, Firefox, Flatpak, Go, IP config. These are desktop/workstation conveniences that don't affect server operation.

**Rationale:** Ansible's full playbook failed because it tried to do everything — one minor role failing (e.g., Netplan on Armbian, or a PPA not existing) broke the whole run. By separating critical path from conveniences, the critical path stays small, testable, and reliable. Each convenience step can be run individually without blocking the rest.

**Alternatives considered:**
- Full Ansible rework: Time-intensive, still fragile across OS differences.
- Single monolithic script: Harder to debug, less transparent.
- Nix/Guix: Overkill for this use case, steep learning curve.

### 3. Data Migration Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     MIGRATION FLOW                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  BEFORE FLASH:                                              │
│    ┌──────────┐    ┌───────────┐                            │
│    │ /home/   │───→│ USB backup│  (rsync -aAXv)            │
│    │orangepi  │    │ drive     │                            │
│    └──────────┘    └───────────┘                            │
│    ┌──────────┐    ┌───────────┐                            │
│    │ /media/  │───→│ temp      │  (rsync)                   │
│    │          │    │ location  │                            │
│    └──────────┘    └───────────┘                            │
│    ┌──────────┐                                             │
│    │ git push │───→ remote (repo already backed up)         │
│    └──────────┘                                             │
│                                                             │
│  FLASH: dd Armbian image → /dev/nvme0n1                    │
│                                                             │
│  AFTER FLASH:                                               │
│    ┌──────────┐    ┌───────────┐                            │
│    │armbian   │←───│ boot,     │                            │
│    │first boot│    │ configure │                            │
│    └──────────┘    │ user/pw   │                            │
│                    └───────────┘                            │
│    ┌──────────┐    ┌───────────┐                            │
│    │ /home/   │←───│ restore   │  (rsync back)              │
│    │orangepi  │    │ from USB  │                            │
│    └──────────┘    └───────────┘                            │
│    ┌──────────┐    ┌───────────┐                            │
│    │ /media/  │←───│ restore   │  (rsync back)              │
│    │          │    │ from temp │                            │
│    └──────────┘    └───────────┘                            │
│    ┌──────────┐                                             │
│    │run       │---→ docker stack live                       │
│    │docker/   │                                             │
│    │run.sh    │                                             │
│    └──────────┘                                             │
│                                                             │
│  TOTAL DATA TO MOVE: ~10 GB /home + ~133 GB /media          │
└─────────────────────────────────────────────────────────────┘
```

**Decision:** Two-phase restore (first boot → network + Docker → restore data → start stack).

**Rationale:** The Docker configs in `~/Documents/` are small (<1 GB). Restoring `/home` first lets us start Docker immediately (it reads configs from `~/Documents/`). `/media` restoration can happen in the background while services are already running — Jellyfin and qBittorrent will pick up files as they appear.

### 4. Network Configuration

**Decision:** Armbian's `armbian-config` for initial setup (hostname, static IP via NetworkManager), then retain the same IP (192.168.2.113).

**Rationale:** Armbian defaults to NetworkManager, not Netplan. Fighting that in favor of Netplan was one reason Ansible broke. Using `nmcli` or `armbian-config` is the OS-native path and survives updates.

**Alternatives considered:**
- Netplan (Ubuntu way): Requires installing netplan package on Armbian, works against defaults.
- Raw /etc/network/interfaces: Works but diverges from Armbian's managed config.

### 5. Repository and Script Structure

**Decision:** Keep the Docker stack configurations and the new provisioning script in this same repo (`orangepi5`), cloned on first boot.

**Rationale:** Single source of truth. The repo already holds all Docker compose files, environment files, and runner scripts. Adding a `setup-armbian.sh` or similar is the minimal addition.

## Risks / Trade-offs

| Risk | Mitigation |
|---|---|
| **Armbian image doesn't support RK3588 hardware transcoding** | Tested in advance — Armbian's rockchip kernel (6.x) includes MPP/VA-API drivers. Verify before flash. |
| **Data loss during backup/restore** | Verify backups with `diff -r` or checksum comparison before wiping NVMe. Keep Ubuntu bootable (boot from SD card) until Armbian is verified. |
| **Docker compose files reference absolute paths** | The `.env` files reference `~/Documents/...` — make sure the restored `/home/orangepi/Documents/` directory structure is identical. |
| **Gluetun WireGuard config lost** | `wg0.conf` is outside the repo (gitignored). It's in `~/orangepi5/wg0.conf` — confirm it's backed up with `/home`. The PIA credentials and key generation script need checking. |
| **PIA credentials expired / failing auth** | Confirmed pre-migration: `pia-wg-config` fails with authentication error, though the existing `wg0.conf` still works. If the config needs regeneration post-migration and credentials are dead, VPN breaks. **Must fix credentials as a post-migration task.** |
| **Docker image bloat will accumulate again** | After cleanup (150 GB freed), the same pattern of old images/volumes will recur without periodic pruning. Need automated cleanup cron. |
| **New Armbian kernel breaks a Docker service** | Test each container after migration. Keep the Ubuntu NVMe untouched until all services are verified. |
| **Ansible partial failure pattern repeats** | That's why we're replacing Ansible with a focused script for critical path. No cross-role dependencies, no external role downloads. |
| **Downtime during migration** | Acceptable — the box can be offline for a few hours. The plan minimizes downtime to the flash + restore window (~1-2 hours for 143 GB data transfer). |

## Migration Plan

### Phase 0: Preparation (on current Ubuntu)
1. Clean up Docker junk (already done: ~150 GB freed)
2. Empty Trash, drop browser caches
3. Push latest repo changes to remote
4. Disable cron jobs (so nothing writes during backup)
5. Run health check on all Docker containers
6. Verify `wg0.conf` exists and is complete
7. Note current installed packages (for convenience layer)

### Phase 1: Backup
1. `rsync -aAXv /home/orangepi/ /mnt/backup-drive/home-backup/`
2. `rsync -aAXv /media/ /mnt/temp-media-store/media-backup/`
3. Verify backup integrity
4. `sudo docker save` any non-pulled images (or just note them)

### Phase 2: Flash
1. Write Armbian image to NVMe via SD card or USB (following existing `flash-image-ansible/` process, but with Armbian image)
2. First boot: set password, hostname, network (via `armbian-config` or first-run wizard)

### Phase 3: Restore
1. Mount backup drive, restore `/home/`
2. Clone this repo
3. Run critical-path setup (Docker install, network, storage mount)
4. Restore `/media/`
5. Run `docker/run.sh` to start all services
6. Verify each service is operational

### Phase 4: Convenience (as needed)
- VS Code, RustDesk, Firefox, Flatpak apps, Go toolchain
- Run individually, not as a combined playbook

### Rollback
- Keep Ubuntu NVMe untouched until Armbian is verified for 48 hours
- If rollback needed: boot from SD card with the current Ubuntu backup, dd the previous Ubuntu image back, restore files from the same backup

## Post-Migration Work (confirmed)

These items are outside the core migration flow but required before the system is fully healthy:

- **PIA credentials**: `pia-wg-config` fails with authentication error on the current system. The existing `wg0.conf` still works, so the migration should proceed with backing it up as-is. After migration, debug and fix the PIA credentials so the config can be regenerated when needed.
- **Docker auto-prune**: Add a cron job or systemd timer to regularly prune unused Docker images, volumes, and build cache. Prevent the 150 GB bloat from recurring. (See tasks section 9.)

## Open Questions

- The user has a Copyparty container that wasn't previously documented in the repo's docker-compose files — we should decide whether to add it to the stack or manage it separately.

## Baseline: Pre-Migration System State

Recorded 2026-09-26. Use these values to verify the Armbian setup is identical.

### Host
- **OS**: Ubuntu 22.04.5 LTS
- **Kernel**: 5.10.160-rockchip
- **Hostname**: localhost (transient)
- **Machine ID**: 8f893751d94a8b2ddb80eb0065b95bc6

### Network (eth0)
- **IP**: 192.168.2.113/24
- **Gateway**: 192.168.2.1
- **DNS**: 8.8.8.8
- **MAC**: 0a:79:72:f3:0f:3b
### Storage
- **NVMe**: /dev/nvme0n1p2 — 939G total, 166G used, 735G free (19%)
- **Boot**: /dev/nvme0n1p1 — 511M, /boot/firmware
- **Firmware**: /dev/mtdblock0 — 16M (bootloader)
- **BTRFS RAID1**: commented out in fstab (drives normally powered off)

### Running Containers (6)
| Container | Status | Ports |
|---|---|---|
| gluetun | Up (healthy) | 8888, 8388, 6881, 8080, 9117, 11470 |
| qbittorrent | Up | through gluetun network |
| jackett | Up | through gluetun network |
| stremio | Up | through gluetun network |
| jellyfin | Up | 8096, 8920, 7359/udp, 1900/udp |
| copyparty | Up | 3923 |

### Container Images
- qmcgaw/gluetun
- lscr.io/linuxserver/qbittorrent:latest
- lscr.io/linuxserver/jackett:latest
- lscr.io/linuxserver/jellyfin:latest
- stremio/server:latest
- copyparty/ac:latest

### Copyparty Config
- Cmd: `--http-only -v /media:media:r:c,e2d,e2t` (serves /media read-only+copy)

### Cron Jobs
| When | What | Runs as |
|---|---|---|
| `0 0 * * *` | `/home/orangepi/Github/orangepi5/docker/docker_pull.sh` | user + root |
| `0 3 * * *` | `cd ~/Github/orangepi5/docker && sudo ./run.sh` | root |

### Service URLs
| Service | URL |
|---|---|
| Jellyfin | http://192.168.2.113:8096 |
| qBittorrent | http://192.168.2.113:8080 |
| Jackett | http://192.168.2.113:9117 |
| Copyparty | http://192.168.2.113:3923 |

### VPN Status
- **Provider**: PIA (Private Internet Access)
- **Region**: Toronto, Canada
- **Public IP**: 66.56.81.91
- **Config file**: `~/Github/orangepi5/wg0.conf` (250 bytes, last generated Aug 20)
- **Credentials file**: `~/Github/orangepi5/secrets` (gitignored)
- **Known issue**: `pia-wg-config` fails auth, but existing wg0.conf works
