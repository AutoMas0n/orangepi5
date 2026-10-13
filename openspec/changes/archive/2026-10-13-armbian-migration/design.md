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

**Staging and the unplugged-backup policy:** the image and `rkspi_loader.img` are copied onto the Pi's **own** disk (`/home/orangepi/Downloads/armbian-migration/`, verified byte-identical) and the backup NVMe is then unmounted, powered off and physically removed. From the write step until the restore, the only USB storage attached is the boot medium — so there is no way to aim a `dd` at the backup by accident, and no stale mount can be written to. The backup drive returns only for the restore (5.5/6.2). This is a deliberate response to a real incident: the enclosure was unplugged mid-use and the kernel, still holding the mount, logged ext4 journal-abort and read-only-remount errors for a device that was no longer present. Nothing was damaged, but it made clear that a mounted backup drive is a liability during a destructive phase.

**Read the source before overwriting it:** in the live environment the image lives on the old rootfs — the partition being destroyed. So 3.8 mounts the old rootfs **read-only**, copies the image + its `.sha256` + the loader into `/dev/shm` (tmpfs, ~2 GB of 8 GB RAM), verifies the hash there, and only then unmounts and `dd`s. Streaming the image off a mounted filesystem while `dd` overwrites the underlying device is exactly the kind of read-after-write corruption this avoids.

### 8. Steering the Boot Without a Console

**Problem:** the medium exists because the NVMe cannot be wiped while running from it — but U-Boot's `boot_targets=mmc0 mmc1 nvme scsi mtd2 mtd1 mtd0 usb0 pxe dhcp` puts `nvme` **before** `usb0`, and the NVMe held a bootable Ubuntu. A plain `reboot` therefore returned to Ubuntu, and with `CONFIG_KEXEC` unset (decision 7) there is no RAM-image escape. A hands-off switch looked impossible without someone at the F2 boot menu.

**Decision:** replace the *old* system's `/boot/firmware/boot.scr` (preserved as `boot.scr.orig`) with a tiny script that scans `usb0` first and falls back to the original:

```
usb start
if test -e usb 0:1 /boot/boot.scr; then setenv devtype usb; setenv devnum 0; run scan_dev_for_boot_part; fi
setenv devtype nvme; setenv devnum 0; setenv distro_bootpart 1; setenv prefix /
load nvme 0:1 ${scriptaddr} /boot.scr.orig
source ${scriptaddr}
```

**Why this shape:** the env already carries `boot_prefixes=/ /boot/` and `boot_scripts=boot.scr.uimg boot.scr`, so the medium's `/boot/boot.scr` is found by the *standard* scan routine (`run scan_dev_for_boot_part`) — no hand-rolled load logic to get wrong. If the USB boot fails, U-Boot prints `SCRIPT FAILED: continuing...`, control returns, and the original Ubuntu script runs: the failure mode of the whole manoeuvre is "back in Ubuntu", never "boots nothing". The script lives on the partition that is about to be wiped anyway, and `mkimage` was already installed.

**Rejected alternatives:** writing `boot_targets` into the SPI environment (`fw_setenv`) — that is bootloader flash, where a wrong offset risks needing maskrom recovery for a purely cosmetic gain; asking the human to pick the device at the F2 menu — works, but cannot be scripted and needs a body at the console.

**Result:** the board booted the medium unattended, answering 69 s after `reboot`.

**Corollary — clone UUIDs are a trap:** the medium's rootfs is a byte-copy of the image, so it advertised the *same* root UUID once the NVMe was flashed. The initramfs resolved `rootdev=UUID=…` to the medium, and the first "new system" boot was silently running off USB. Give one side a fresh UUID (`tune2fs -U`) and update **both** references in it — `/boot/armbianEnv.txt` (`rootdev=`) and `/etc/fstab` — or remove the medium before the first NVMe boot. Check `findmnt -no SOURCE /`; the hostname proves nothing because both systems are `orangepi`.

### 9. VPN: PIA's WireGuard provisioning moved

**Decision:** keep gluetun in `custom` + `wireguard` mode (performance was an explicit requirement — 389 Mbps through the tunnel vs 630 Mbps raw), but generate `wg0.conf` with a new `docker/refresh-wireguard.sh` that wraps **PIA's own maintained** `pia-foss/manual-connections` scripts.

**What changed upstream:** `pia-wg-config` — the Go tool this repo relied on — POSTs to `privateinternetaccess.com/api/client/v2/addKey`. That path now returns **404** for every variation (form, JSON, GET, no-www). PIA moved key registration onto the VPN server itself and gated it behind a token:

1. `POST https://www.privateinternetaccess.com/api/client/v2/token` (form `username`/`password`) — my first probe got 401 only because it sent no form fields
2. region → WireGuard server from `https://serverlist.piaservers.net/vpninfo/servers/v6`
3. `GET https://<wg-hostname>:1337/addKey?pt=<token>&pubkey=<pubkey>`, TLS verified against `ca.rsa.4096.crt`

**Consequence of the old premise:** the plan claimed "`pia-wg-config` fails auth but the existing `wg0.conf` still works, so the VPN is fine". That was false. A host-level test showed the tunnel sending 888 B and receiving **0 B** — its endpoint had been retired. The misleading "authentication failure" was a 404 being misreported.

**Rejected alternative:** PIA over OpenVPN via gluetun's native provider. It works with credentials alone (three regions verified) and is the documented fallback, but it is slower, and WireGuard performance was a hard requirement.

### 10. What was lost, and why (backup coverage)

**What happened.** Task 2 backed up `/home/orangepi` and `/media`. The plan asserted the stack's configuration lived in `~/Documents` — and the containers' own `.env` files appeared to agree. Both were wrong in a way nobody checked: `run.sh` runs as root, so Compose expanded `~/Documents` against **`/root`**. The live state therefore lived in `/root/Documents`: qBittorrent's torrent list, `.fastresume` data and categories, Jackett's indexer definitions, Jellyfin's library and settings, copyparty's config.

**Why it was unrecoverable.** Two failures compounded. The state existed only on the old rootfs — not in git, and not anywhere else on the backup drive (a full search of that drive found only game dumps). And by the time it was noticed, the migration had already written the image, scattered `resize2fs` metadata across the 953 GB device, and restored 136 GB — over the region the old filesystem occupied, because ext4 allocates from the start and the old system had ~155 GB used. A read-only scan of the entire device for old directory entries, INI/JSON config markers and bencoded torrent blobs found **nothing that was not our own new data**.

**What survived, and why.** Everything committed to git: compose files, `.env`s, `secrets`, `wg0.conf`, the `.md` docs, and — by luck — the Jackett API key, which had been committed as a qBittorrent search-plugin config. That single fact is the argument for decision 13.

**The rule that replaces the assumption:** coverage must be *derived*, never asserted. `scripts/verify-coverage.sh` (task 2.9) resolves every bind-mount source from the compose files and asserts each lies inside the declared backup set; it must run before any destructive step. The proximate cause is also fixed at the source: every `.env` now uses absolute paths (`/home/orangepi/Documents/...`), so `HOME` can no longer decide where state lands.

### 11. Boot resilience and a self-healing tunnel

**Decision:** the stack must come back by itself after a reboot, and recover from a dead tunnel without a human.

**What was broken:** `gluetun` had **no restart policy** while the other four containers had `unless-stopped`. A reboot would have started Docker, brought up `jackett`/`qbittorrent`/`stremio`/`copyparty` — and left them without networking, because they run in gluetun's network namespace. The single most likely "my server is down" scenario was baked in.

**Now:** gluetun has `restart: unless-stopped`; `media-stack.service` runs `run.sh` at boot (ordered after `docker.service` and `network-online.target`) so the start sequence is deterministic; and `vpn-watchdog.timer` checks gluetun every 5 minutes and escalates — restart the whole stack after 3 consecutive unhealthy cycles, then mint a fresh WireGuard config after 6 (a restart alone cannot fix a retired endpoint). State lives in `/var/lib/vpn-watchdog.fails`, events go to journald.

**Verified:** an unattended `systemctl reboot` brought back all five containers, gluetun healthy, tunnel up at `45.89.249.204`, WebUIs answering, watchdog at 0 failures.

### 12. Retiring Jellyfin

**Decision:** drop Jellyfin from the stack rather than rebuild it.

**Rationale:** it lost the most state (library database, watch history, metadata) with no cheap way back, and it was the only service needing a hardware-specific fix — the old compose passed `/dev/dri/renderD129`, which the new kernel does not expose (`card0`, `card1`, `renderD128` only), so the container could not even start. Carrying a service that needs bespoke patching, whose state is gone, is worse than removing it deliberately. Removed from `run.sh`, the pull list and the docs; compose dir deleted (recoverable from git history); port 8096 no longer expected.

### 13. Tidiness and a single source of truth

**Decision:** delete what is dead, and make the live configuration recoverable from git.

- removed the dead Go toolchain and `pia-wg-config` (installed only to build a tool whose endpoint no longer exists), my exploratory clone, and stray credential/test files
- `secrets` reduced to `PIA_USER`/`PIA_PASS`; the OpenVPN fallback credentials are not kept because gluetun is WireGuard-only here
- deleted the stale nested `docker/docker/` duplicate, the typo'd `docker/qbittorrent/qbittorent/` directory, the dropped Jellyfin compose, and the inert `qBittorrent-data.conf` mount + file (qBittorrent reads `qBittorrent.conf`; the mount never worked — as the file's own comment suspected)
- the recovered API key is kept as `docker/qbittorrent/reference/jackett.json`
- **the rule:** if a piece of configuration is not in git, it does not exist. The live stack config (compose file, `.env`s, `run.sh`, `docker_pull.sh`, `refresh-wireguard.sh`, tuned `qBittorrent.conf`) must be committed (task 9.7) — today it is single-copy on the Pi, which is exactly the condition that lost the last set

### 14. WireGuard throughput: measure against the same server, and know the hardware ceiling

**Decision:** treat throughput numbers as path-dependent until proven otherwise, and record the actual ceiling of this board.

The Orange Pi 5 has a **single 1 GbE** port (`end0`, negotiated 1000 Mb/s full duplex). The 3 Gbps at the modem is irrelevant to this box — ~940 Mbps of payload is the hard ceiling, and only the 5 Plus/5B (2.5 GbE) go higher. So the first reading of *389 Mbps through the tunnel vs 630 raw* was never a like-for-like comparison, and the later evidence shows why: on the same distant server a **single stream through the tunnel hit 570 Mbps while the "raw" single stream got 408** — the number was tracking the server and route, not the tunnel.

Measured properly, four streams against one Canada-local server:

| Path | Throughput |
|---|---|
| Raw (no VPN) | **801 Mbps** |
| Through WireGuard | **602 Mbps** (75% of raw) |

During the tunneled run `cpu0` sat at **85%** while aggregate CPU stayed low: the cost is RX softirq plus WireGuard crypto, concentrated on one core because **RPS is disabled** (`/sys/class/net/end0/queues/rx-0/rps_cpus` = `00`). The tunnel MTU was already **1440**, which is optimal for 1500-byte paths, so no MTU tuning is warranted.

**Consequences:** kernel WireGuard with ARMv8 chacha20 on RK3588 lands around here *per flow*; the kernel `wireguard` module is loaded (`libchacha20poly1305`, `libcurve25519`), so this is the in-kernel path, not userspace. Torrents use many connections and aggregate better than a single speedtest stream, so real download throughput should exceed this single-flow figure. Spreading RX across cores (RPS/multi-queue, or pinning the softirq) is the obvious remaining lever — **deliberately not applied**: it is a system-wide networking change and not worth making on the eve of a burn-in for a client that is already performing well.

### 15. TorrentLeech via Jackett: the login is the username, not the email

**Decision:** record the two non-obvious facts that cost real time, so the next person does not repeat them.

- **TorrentLeech authenticates on the bare username** (`4543562a`); submitting the email address is rejected with "Invalid Username/password combination". Diagnosis was confused for a while because a *captcha* is present on the login page and the tunnel IP was an easy suspect — it was neither: a direct login from the home IP (`174.93.12.62`) was rejected identically, and once the username was corrected the login returned HTTP 302 from both the home IP and the VPN exit.
- **Jackett's admin API** needs a session cookie from `/UI/Login`, and its config payload is an **array of `{id, value}`** — `ConfigurationData.LoadConfigDataValuesFromJson` matches fields by `id`, so `{name, ...}` or a plain dict produces a cast error. Jackett **validates the login while saving**, so bad credentials return HTTP 500 and persist nothing; a good save returns 204.

This is a good outcome for the tracker/VPN question: TorrentLeech works normally from PIA's Toronto exit, so there is no reason to move Jackett outside the tunnel.

### 16. The qBittorrent search tab: a defect in the image, documented rather than papered over

**Decision:** stop guessing, prove where the failure is, and hand it over with the evidence — the failing component is qBittorrent itself, not this stack.

A search request hangs for ~50 seconds. During that time qBittorrent **forks itself** (`/app/qbittorrent-nox`, identical argv, parent = the qBittorrent process) and that child burns **99% of a core**; no `python3` child is ever created and Jackett records no incoming request. The request finally returns a job id, the job ends `Stopped` with 0 results, and `search/results` answers `Not Found`.

Every layer underneath is demonstrably healthy, invoked exactly as qBittorrent would (uid 30000): `python3 nova2.py --capabilities` emits the precise XML the binary expects (`<capabilities><jackett>…`), `python3 nova2.py jackett movies matrix` returns the full TorrentLeech result set with working `/dl/torrentleech/...` links, the engine is present in the data directory at mode 444 with `# VERSION: 1.53` (qBittorrent rewrites it itself), and qBittorrent's own log says `Found Python executable. Name: "python3". Version: "3.14.7"`.

The remaining suspect is the image: `lscr.io/linuxserver/qbittorrent:latest`, build `5.2.4_v2.0.15-ls479`, built **2026-09-29** — one day old at the time of writing, and the only component whose behaviour changed without anyone touching it.

**Resolved as an accepted limitation** (user decision, 2026-09-30): the image-swap route was **declined**, so this defect is deliberately not pursued further and nothing is pending on it. The supported substitute — and where searches should be run — is **Jackett's own UI on `:9117`**, which performs the same TorrentLeech searches.

### 17. Retiring Copyparty (rclone does the job)

**Decision:** remove Copyparty from the stack. `rclone` is already installed on the host (`/usr/bin/rclone`) and covers the same ground — it serves and mounts directories directly, with no extra container, no WebDAV port and no second copy of the access story. It had no state worth preserving: its `/cfg` volume held 56 KB of defaults and the service was read-only against `/media`. (User decision, 2026-10-04, during the burn-in window.)

**What was removed:**

- the `docker/copyparty/` compose directory, and its line in `docker/run.sh` — so the stack is now **4 services** (gluetun, qbittorrent, jackett, stremio), not 5
- `copyparty/ac` from `docker/docker_pull.sh`
- the container and image on the Pi (the image was unused afterwards, so it is a candidate for the weekly prune)
- `/home/orangepi/docker-data/copyparty` (56 KB; nothing in it was unique) and port `3923`
- its rows in `scripts/burnin-check.sh`, the verify list and the docs

**Consequences:** anything that pointed at `http://192.168.2.113:3923` — a browser bookmark, a `davfs` mount, an rclone remote — needs repointing at whatever `rclone serve` now exposes. The coverage rule is unaffected: `scripts/verify-coverage.sh` derives its list from the compose files, so a deleted service leaves the backup set smaller, never stale. Recorded as decision 12 was for Jellyfin, and by the same rule: *retire a service deliberately rather than leaving it as a half-working copy.*

## Risks / Trade-offs

| Risk | Mitigation |
|---|---|
| **Armbian image doesn't support RK3588 hardware transcoding** | Tested in advance — Armbian's rockchip kernel (6.x) includes MPP/VA-API drivers. Verify before flash. |
| **Data loss during backup/restore** | Verify backups with `diff -r` or checksum comparison before wiping NVMe. The Ubuntu install on the NVMe is *not* preserved by this plan — rollback means re-flashing a boot medium and restoring from the backup NVMe, not booting the old system. |
| **Pre-seeded image no longer matches the published checksum** | The flashed `.img` is a modified derivative: keep the pristine `.img.xz` + `.sha` + `.asc` (verified against Armbian's key) next to it, and record the derivative's own sha256. Verify the derivative, never the published digest, against what was flashed. |
| **Hash recorded from a file that was still being modified** | Happened: the derivative's hash was taken *before* a last in-image tidy-up (`rm -rf /run/…`) mutated the filesystem, so the recorded digest (`4d40ba14…`) never matched the file on disk. The authoritative value is computed only **after the last write** — here `5af0cf0de5d6445d7f1ec24e6d66fdca603aac8bfb8a6a38e1917bf262f39058`, confirmed on both the source and the copy. Any hash in this plan is only trustworthy if it post-dates the final `umount` of the image. |
| **Reading the source rootfs while `dd` overwrites it** | 3.8 copies the image into `/dev/shm` and unmounts the old rootfs *before* writing, so the read and the overwrite never overlap. |
| **Duplicate root UUID between the image and a clone of it** | Bitten in practice: after flashing, the boot medium and the NVMe both advertised `UUID=17c1be52-…`, and the initramfs quietly resolved `rootdev` to the medium. Detect with `findmnt -no SOURCE /` (not hostname). Fix with `tune2fs -U` plus *both* references (`armbianEnv.txt` + `/etc/fstab`), or by removing the medium first. |
| **Service state outside the backup set** ⚠️ **realized — worst outcome of this migration** | `~` in `.env` resolved to `/root` because the stack script runs as root, so the state sat in `/root/Documents` while the backup covered `/home` + `/media`. Lost: qBittorrent's torrents/resume data, Jackett's indexers, Jellyfin's library. Mitigation now: absolute paths in every `.env`, and a machine-checked coverage script (task 2.9) that must pass before any destructive step. |
| **VPN endpoint retired by the provider** | Happened silently: the tunnel handshook with nobody (`0 B received`) while `docker ps` still said "Up". Detect by egress-IP comparison, not container status; recover with `docker/refresh-wireguard.sh`; automated by `vpn-watchdog.timer`. |
| **A container that has no restart policy** | `gluetun` had none while its four dependents did — one reboot away from taking the whole VPN stack down. All five now `unless-stopped`, plus an ordered systemd unit at boot. |
| **Live configuration existing only on the host** | The working stack config was single-copy on the Pi for the whole migration — the same failure mode as the lost state. Mitigation: task 9.7 commits it; rule: not in git = does not exist. |
| **Static IP is never reachable on first boot** | Worst case the box needs a console after all. Mitigations: name-glob netplan match (works for `eth0`/`end0`), SSH key *and* password both enabled, and the plan keeps monitor+keyboard as a documented fallback in HUMAN.md. |
| **Docker compose files reference absolute paths** | The `.env` files reference `~/Documents/...` — make sure the restored `/home/orangepi/Documents/` directory structure is identical. |
| **Gluetun WireGuard config lost** | `wg0.conf` is outside the repo (gitignored). It's in `~/Github/orangepi5/wg0.conf` — confirm it's backed up with `/home`. The PIA credentials and key generation script need checking. |
| **PIA credentials expired / failing auth** | Confirmed pre-migration: `pia-wg-config` fails with authentication error, though the existing `wg0.conf` still works. If the config needs regeneration post-migration and credentials are dead, VPN breaks. **Must fix credentials as a post-migration task.** |
| **Docker image bloat will accumulate again** | After cleanup (150 GB freed), the same pattern of old images/volumes will recur without periodic pruning. Now mitigated: weekly `docker system prune -f` in root cron (task 9.2), deliberately **without** `--volumes` (bind-mount stack) — see `docker/README.md`. |
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
2. Stage the images on the Pi's own disk and unplug the backup NVMe (decision 7)
3. Write the pre-seeded image to a boot medium (USB stick or SD), boot it, wipe the NVMe, flash `rkspi_loader.img` + the image
4. First boot is headless: no console, no wizard — SSH is up at 192.168.2.113 immediately

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

These items are outside the core migration flow but were required before the system could be called healthy:

- ~~**PIA credentials**~~ — **done.** The old premise ("the existing `wg0.conf` still works") was false: its endpoint had been retired and the tunnel was handshaking with nobody. Regeneration now works via `docker/refresh-wireguard.sh` (decision 9).
- ~~**Copyparty to docker-compose**~~ — **done, then retired.** It was a compose service in the restored repo (`docker/copyparty/`) and started by `run.sh`; on 2026-10-04 it was **removed from the stack** because rclone covers the same ground natively — see decision 17.
- ~~**Docker auto-prune**~~ — **done (task 9.2 / 10.6).** Weekly `docker system prune -f` in root cron (Sun 04:30), logging to `/var/log/docker-prune.log`. Installed plain, **not** `--volumes -f` as originally written: the stack uses bind mounts, so unused *named* volumes are rare while the flag will happily delete volumes belonging to any stopped container. First run reclaimed 164 MB of dangling layers plus the retired Jellyfin image (797 MB), taking reclaimable space from 1.885 GB to 66 MB.
- **qBittorrent search tab**: broken in the current image; see decision 16 and task 10.4.

## Open Questions

- **Does the search tab work on another qBittorrent image tag?** This is the one unresolved service-level defect (decision 16). Everything it depends on is proven working, so the test is cheap: run the same tag family one version back and repeat a single search.
- **Should RX processing be spread across cores (RPS/multi-queue)?** It is the remaining WireGuard headroom lever (decision 14). Not applied deliberately — revisit only if real torrent throughput disappoints.

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
