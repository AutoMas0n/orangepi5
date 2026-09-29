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

**Decision:** Pre-seed the static address into the image itself with **netplan (renderer: `systemd-networkd`)**, matching the Ethernet device by name glob (`e*`) instead of a specific interface name. Retain the same address (192.168.2.113).

**Rationale (corrected after inspecting the actual 26.8.1 image):** This Armbian build does **not** ship NetworkManager — `nmcli` and `/usr/sbin/NetworkManager` are absent, and `/etc/network/interfaces` does not exist. The active stack is **netplan.io → systemd-networkd**, with Armbian's own `/etc/netplan/10-dhcp-all-interfaces.yaml` doing DHCP for `e*`. The original version of this decision (written before inspecting the image) assumed NetworkManager and `nmcli`; that was wrong for this image. The static config was therefore folded **into Armbian's own netplan file** rather than added as a second, competing file — two match-based entries for the same device would race, and networkd/netplan precedence would decide the winner non-obviously.

**Why name-glob matching:** the pre-migration box reports `eth0`, but Armbian's udev-based naming may produce `end0` or `enp*`. `e*` covers all of them and is Armbian's own default pattern. Matching by MAC was rejected because the baseline MAC (`0a:79:...`) is locally administered and may be regenerated.

**Alternatives considered:**
- `nmcli` / NetworkManager: not installed; would mean pulling in a whole extra network stack.
- Raw `/etc/network/interfaces`: not even installed, and diverges from Armbian's defaults.
- A separate netplan file for the static address: risks the DHCP entry winning; editing Armbian's file is unambiguous.

### 5. Repository and Script Structure

**Decision:** Keep the Docker stack configurations in this same repo (`orangepi5`), cloned on first boot. The critical-path setup is executed as documented command sequences in the task list.

**Rationale:** Single source of truth. The repo already holds all Docker compose files, environment files, and runner scripts. Inline commands are more transparent and reliable than a monolithic provisioning script for a one-time migration.

### 6. Image Pre-Seeding (headless first boot)

**Decision:** Patch the downloaded image before flashing so the first boot needs no console at all:

| What | Where | Value |
|---|---|---|
| User + password | `/etc/passwd`, `/etc/shadow` | `orangepi` (uid/gid 1000), groups `sudo,video,render,audio,plugdev,netdev`; password `orangepi` (root password set the same) |
| SSH on, password auth | `/etc/ssh/sshd_config.d/10-migration-headless.conf` | `PasswordAuthentication yes`, `PubkeyAuthentication yes`, `PermitRootLogin prohibit-password` |
| Agent/human key | `/home/orangepi/.ssh/authorized_keys` | public key, `600` + owner 1000 |
| Static IP | `/etc/netplan/10-dhcp-all-interfaces.yaml` | `192.168.2.113/24`, gw `192.168.2.1`, dns `8.8.8.8` |
| Hostname | `/etc/hostname`, `/etc/hosts` | `orangepi` (image ships `orangepi5`) |
| Console wizard | `/root/.not_logged_in_yet` | deleted — its presence is what triggers `armbian-firstlogin` |

**Rationale:** the migration is designed to be driven over SSH from the start. Without pre-seeding, the only way in on first boot is a monitor+keyboard (or serial console) at the wizard, and any first-boot failure is invisible until the human is physically present. Pre-seeding makes the flash step the only remaining physical act (inserting a medium and power-cycling), and turns 4.1/4.2 from "configure" into "verify".

**Mechanism note:** this image predates/omits the old `armbian_first_run.txt` mechanism; the modern build triggers `armbian-firstlogin` only from `/etc/profile.d/armbian-check-first-login.sh` when `/root/.not_logged_in_yet` exists, which is why deleting that one flag is enough. `systemd-firstboot.service` is already masked in the image. Editing the image directly (mount, chroot, `netplan generate`, `sshd -t`) is more deterministic than hoping a wizard honours a config file.

**Verified outcome:** `netplan generate` and `sshd -t` both pass in the patched image; `sshd -T` reports `passwordauthentication yes`, `permitrootlogin without-password`, `pubkeyauthentication yes`, `permitemptypasswords no`.

### 7. Flash Medium and the KEXEC Dead End

**Decision:** Use a **USB stick** (preferred) or an **SD card** as the staging boot medium. The agent writes it with `dd` from the image already sitting on the backup NVMe.

**Rationale:** the NVMe cannot be wiped from the system running on it without risk. Armbian 26.8.1 for orangepi5 is a **single GPT partition** (ext4 root starting at sector 32768; the image is only 1.68 GiB, bootloader at raw sectors 64/16384), and `armbian-resize-filesystem.service` grows the rootfs to fill the 953 GB NVMe on first boot — so a plain `dd` of the image to `/dev/nvme0n1` is the whole procedure, no manual partitioning.

**Rejected alternative — boot a flash environment entirely from RAM:** this was the preferred no-extra-hardware option, but the running kernel (5.10.160-rockchip) has **`CONFIG_KEXEC` and `CONFIG_KEXEC_FILE` unset** and `kexec-tools` is not installed, so a kernel cannot be loaded from the running system. Without kexec the only hardware-free option is writing the NVMe *in place* from the running Ubuntu (quiesce to single-user, `swapoff`, `fsfreeze`, run a static busybox from `/dev/shm`, `dd` from the backup NVMe). That was rejected as the default because the filesystem being written is still mounted and live, and a mid-write failure leaves no bootable system — recovery would need maskrom mode + `rkdeveloptool` from a PC. Kept only as a documented last resort for a situation with no removable medium at all.

## Risks / Trade-offs

| Risk | Mitigation |
|---|---|
| **Armbian image doesn't support RK3588 hardware transcoding** | Tested in advance — Armbian's rockchip kernel (6.x) includes MPP/VA-API drivers. Verify before flash. |
| **Data loss during backup/restore** | Verify backups with `diff -r` or checksum comparison before wiping NVMe. The Ubuntu install on the NVMe is *not* preserved by this plan — rollback means re-flashing a boot medium and restoring from the backup NVMe, not booting the old system. |
| **Pre-seeded image no longer matches the published checksum** | The flashed `.img` is a modified derivative: keep the pristine `.img.xz` + `.sha` + `.asc` (verified against Armbian's key) next to it, and record the derivative's own sha256 (`4d40ba14…ef7ae`). Verify the derivative, never the published digest, against what was flashed. |
| **Static IP is never reachable on first boot** | Worst case the box needs a console after all. Mitigations: name-glob netplan match (works for `eth0`/`end0`), SSH key *and* password both enabled, and the plan keeps monitor+keyboard as a documented fallback in HUMAN.md. |
| **Docker compose files reference absolute paths** | The `.env` files reference `~/Documents/...` — make sure the restored `/home/orangepi/Documents/` directory structure is identical. |
| **Gluetun WireGuard config lost** | `wg0.conf` is outside the repo (gitignored). It's in `~/Github/orangepi5/wg0.conf` — confirm it's backed up with `/home`. The PIA credentials and key generation script need checking. |
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
1. Connect external NVMe via USB-C enclosure, verify mounted (e.g. `/mnt/backup-nvme`)
2. Create backup parent directory: `mkdir -p /mnt/backup-nvme/armbian-migration-backup`
3. `rsync -aAXv /home/orangepi/ /mnt/backup-nvme/armbian-migration-backup/home-backup/`
4. `rsync -aAXv /media/ /mnt/backup-nvme/armbian-migration-backup/media-backup/`
5. Verify backup integrity (file count / checksum)
6. `sudo docker save` any non-pulled images (or just note them)

### Phase 2: Flash
1. Pre-seed the image ahead of time: SSH, `orangepi`/`orangepi`, static IP, hostname (decision 6) — done before any hardware is touched
2. Write the pre-seeded image to a boot medium (USB stick or SD), boot it, wipe the NVMe, flash `rkspi_loader.img` + the image
3. First boot is headless: no console, no wizard — SSH is up at 192.168.2.113 immediately

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
- **Copyparty to docker-compose**: The Copyparty container runs manually (not in any compose file). Add it to the docker-compose stack so it's managed alongside the other services.

## Open Questions

None currently.

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
