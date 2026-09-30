> **📋 Human companion file**: Before starting, give the human `openspec/changes/armbian-migration/HUMAN.md` — it tells them exactly when to plug in drives, boot from SD, etc. The tasks below reference 👤 sections that need human physical action.

> **⚠️ What went wrong here — read this before trusting any backup step.** Task 2 backed up `/home/orangepi` and `/media` because this plan *asserted* that the stack's configs live in `~/Documents`. They did not. `run.sh` runs as root, so `~` expanded to `/root`, and the live service state (qBittorrent's torrent list, `.fastresume` data and categories; Jackett's indexer definitions; Jellyfin's library and settings) sat in **`/root/Documents` — outside the backup set**. It was destroyed with the old rootfs, and the blocks that held it were then overwritten by the migration itself (image + `resize2fs` metadata + the 136 GB restore), so raw recovery was impossible: a full-device scan found no old filesystem data at all. The 133 GB of media survived intact, as did anything committed to git (`secrets`, `wg0.conf`, the compose files, and — luckily — the Jackett API key stored in `docker/qbittorrent/…/jackett.json`). See design decisions 10 and 13, and task 2.9: the fix is a machine-checked coverage rule, never an assumption about paths.

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

- [ ] 2.9 **Backup coverage check (mandatory before any destructive step).** Resolve every bind-mount source in every compose file and every directory the stack writes to, and assert each lies inside the declared backup set (`/home/orangepi`, `/media`, the repo, `secrets`, `wg0.conf`). Implement as `scripts/verify-coverage.sh` so it can be re-run. This task exists because its absence cost the stack its entire configuration: a plan-level *assumption* about where configs live is not evidence, and coverage must be derived from the configs themselves.

## 3. Download Armbian and Prepare Flash Medium

> **👤 Human required**: in the end the only human action needed here was inserting the medium (3.5). 3.6 and 3.9 were completed by the agent over SSH — see design.md decision 8 for how the console-free boot switch was done.
> The agent downloads, verifies, pre-seeds and stages the image (3.1–3.4), boots the medium (3.6) and runs the destructive flash (3.8).
> **The first boot needs no console**: the pre-seeded image (3.3) brings up SSH, the `orangepi`/`orangepi` account and the static IP 192.168.2.113 on its own.
> **No RAM-boot escape hatch**: the running kernel has `CONFIG_KEXEC` unset, so a boot medium (USB stick or SD card) is required — see design.md decision 7.
> **The backup NVMe stays unplugged** from 3.5 to 3.8 and comes back for the restore (5.5/6.2). That is why the images were copied onto the Pi's own disk in 3.4: only the boot medium is present while the destructive steps run.

- [x] 3.1 Download the Armbian Trixie current minimal image: `wget https://dl.armbian.com/orangepi5/Trixie_current_minimal` — downloaded first to `/mnt/backup-nvme/armbian-migration-backup/` on the backup NVMe, then **copied to `/home/orangepi/Downloads/armbian-migration/`** on the Pi's own disk (3.4) so the backup drive can be unplugged for the flash. Resolves to `Armbian_26.8.1_Orangepi5_trixie_current_6.18.43_minimal.img.xz` (356,570,828 bytes)
- [x] 3.2 Verify the download checksum — **verified** SHA256 `a7633627a54b6d8c5f03294cbf1b3b998d55b8e1e15cfb5296a3c440b981fcb5` (matches the published `.sha`). Detached `.asc` also verified: Good signature, RSA key `DF00FAF1C577104B50BF1D0093D6889F9F0E78D5` ("Igor Pecovnik <igor@armbian.com>")
- [x] 3.3 Pre-seed the image for a headless first boot (done before flashing, on the pristine extraction):
  - user `orangepi` (uid/gid 1000, groups `sudo,video,render,audio,plugdev,netdev`), password `orangepi`; `root` password also `orangepi`
  - `/etc/ssh/sshd_config.d/10-migration-headless.conf`: `PasswordAuthentication yes`, `PubkeyAuthentication yes`, `PermitRootLogin prohibit-password` (sshd already enabled in the image; `Include` at the top of `sshd_config` means this drop-in wins)
  - `/home/orangepi/.ssh/authorized_keys`: agent/human public key installed (`600`, owner 1000) as an alternative to the password
  - static IP via netplan: `/etc/netplan/10-dhcp-all-interfaces.yaml` (renderer `networkd`, Armbian's own file — **no** competing file) → `192.168.2.113/24`, gateway `192.168.2.1`, DNS `8.8.8.8`, matched by `name: "e*"` so the interface may be `eth0` **or** `end0`
  - hostname `orangepi` (image ships `orangepi5`), `/etc/hosts` updated
  - `/root/.not_logged_in_yet` deleted → the console first-login wizard never runs
  - output: `Armbian_26.8.1_Orangepi5_trixie_current_6.18.43_minimal-orangepi-preconfigured.img` (1,799,356,416 bytes), sha256 `5af0cf0de5d6445d7f1ec24e6d66fdca603aac8bfb8a6a38e1917bf262f39058` — **authoritative**
    - an earlier value (`4d40ba14…ef7ae`) was hashed *before* a final in-image tidy-up (`rm -rf /run/systemd/network /run/sshd`) mutated the filesystem, so it no longer described the file on disk. The re-hashed value above was confirmed on both the source and the copy
  - validated in-image with `netplan generate` and `sshd -t`; the pristine `.img.xz` is kept untouched next to it
- [x] 3.4 Stage the artifacts on the Pi's own disk and eject the backup NVMe:
  - copied to `/home/orangepi/Downloads/armbian-migration/`: the pre-seeded `.img` (verified byte-identical to the source, `5af0cf0d…`), the pristine `.img.xz` + `.sha` + `.asc`, `rkspi_loader.img` (4,194,304 B) and a regenerated `.img.sha256`
  - `README-copies.txt` in that directory records the source device (`/dev/sda`, ASM246X serial `AAAABBBB3054`), the capture time, and the backup contents (`home-backup` 3.2 G, `media-backup` 133 G)
  - the drive was unmounted, **powered off and removed from the USB bus** — it stays unplugged until the restore (5.5/6.2)
  - ⚠️ **device names shuffle**: the enclosure came back as `sda` (a name that previously belonged to a RAID drive) and the stick is `sdd`. Always identify a device by size/model/serial, never by name; the sshd_config and gdisk steps above are name-independent for this reason
- [x] 3.5 Write the **pre-seeded** image to the boot medium (USB stick preferred — the Pi's USB-A ports are free; an SD card works equally well):
     ```bash
     # agent, once the medium is inserted into the Pi and confirmed with lsblk
     sudo dd if=/home/orangepi/Downloads/armbian-migration/Armbian_26.8.1_Orangepi5_trixie_current_6.18.43_minimal-orangepi-preconfigured.img \
             of=/dev/<medium> bs=8M status=progress conv=fsync
     ```
     Verify by read-back: `dd if=/dev/<medium> bs=8M count=215 2>/dev/null | head -c 1799356416 | sha256sum` must print `5af0cf0d…`. This overwrites the whole device.
     Alternative if the agent is not to touch the medium: write the same `.img` yourself from your own machine, then skip to 3.6.
     **Result:** written to `/dev/sdd` (SanDisk Ultra 32 GB — the ex-Ventoy stick, incl. its 9.6 GB ISO, as agreed). 1,799,356,416 B in 127 s (14.2 MB/s), read-back sha256 `5af0cf0d…` **MATCH**. The source hash was re-checked immediately before writing. `fdisk -l` shows the single 1.7 G ext4 partition at sector 32768; the GPT still has its backup header at the old 1.68 GiB offset (`GPT PMBR size mismatch`, `backup GPT table is not on the end of the device`) — expected for an image dd'd onto larger media, and repaired by Armbian on first boot (`sgdisk -e` + `growpart` in `armbian-resize-filesystem.service`) before the rootfs is grown to fill the device.
- [x] 3.6 Boot the flash medium **without a console** (design.md decision 8):
     - a plain `reboot` returns to Ubuntu — the SPI bootloader's `boot_targets=mmc0 mmc1 nvme scsi mtd2 mtd1 mtd0 usb0 pxe dhcp` puts `nvme` ahead of `usb0`
     - solved by replacing the *old* system's `/boot/firmware/boot.scr` (preserved as `boot.scr.orig`) with a small script that scans `usb0` first and falls back to the original — so the worst case is "back in Ubuntu", never "boots nothing"
     - result: the board came up on the medium by itself, answering at 192.168.2.113 **69 s** after the reboot; the medium's rootfs auto-grew 1.7 G → 27.9 G
- [x] 3.7 Wipe the NVMe — **satisfied by 3.8, no `gdisk` run**: the full-image `dd` overwrites the primary GPT and writes a complete, self-consistent table, with `armbian-resize-filesystem` repairing the backup header on first boot. `/dev/mtdblock0` was deliberately left alone (it is bootloader flash, and the loader write below is a proven byte-identical refresh — further writes are pure risk with no benefit)
- [x] 3.8 Flash the bootloader firmware and write the image:
     - payload staged **persistently** on the live medium's own rootfs (`/root/armbian-migration-transfer/`, 25 GB free) instead of only `/dev/shm`, so a botched flash stays retryable across reboots
     - old rootfs mounted **read-only** at `/mnt/old`; image + `.sha256` + `rkspi_loader.img` copied out; `sha256sum -c` OK; then **unmounted before any write**
     - SPI: `/dev/mtdblock0`'s first 4 MiB verified byte-identical to `rkspi_loader.img` (`267d2019…`) → the write is a zero-risk refresh
     - `dd if=<image> of=/dev/nvme0n1 bs=8M conv=fsync` → 1,799,356,416 B in **5 s (377 MB/s)**
     - **read-back verified**: sha256 of the first 1,799,356,416 bytes of `/dev/nvme0n1` = `5af0cf0d…` **MATCH**; `blkid /dev/nvme0n1p1` → `LABEL=armbi_root`, `UUID=17c1be52-…`, exactly the image's `rootdev`
- [x] 3.9 Boot from the NVMe — done by remote `reboot`, no power-cycle and **no need to remove the medium**:
     - ⚠️ **duplicate-UUID trap**: the medium's rootfs is a byte-copy of the image, so it advertised the *same* root UUID. The initramfs resolved `rootdev=UUID=17c1be52-…` to the medium, and the first NVMe boot silently came up on `/dev/sda1`. Detected by checking `findmnt -no SOURCE /` (both systems report hostname `orangepi`, so the hostname proves nothing)
     - fixed by giving the NVMe rootfs a fresh UUID (`tune2fs -U`) and updating both references in the new install — `/boot/armbianEnv.txt` (`rootdev=`) and `/etc/fstab` — leaving the medium's UUID untouched so it remains a valid rescue system
     - result: `ROOT: /dev/nvme0n1p1 930.2G ext4`, `Armbian 26.8.1 trixie`, static IP answering, rootfs auto-grown from 1.68 GiB to 930 GB
     - the medium is now optional: keep it inserted as a rescue system (it holds the image copy plus `secrets`/`wg0.conf` backups at `/root/armbian-migration-transfer/`) or remove it at leisure — boot order prefers `nvme` either way

## 4. First Boot & Armbian Setup

> **👤 Human required**: nothing — the first boot is headless. The console wizard is disabled in the image and every wizard setting was pre-seeded in 3.3.
> A monitor+keyboard or serial console is only needed if the box fails to appear on the network.

- [x] 4.1 First boot verified: SSH to `orangepi@192.168.2.113` works, hostname `orangepi`, user uid 1000 in `sudo,video,render,audio,plugdev,netdev`, no console wizard ever appeared, timezone `Etc/UTC` (unchanged from the pre-migration system). Armbian also grants the first user passwordless sudo.
- [x] 4.2 Static IP verified: `192.168.2.113/24` on **`end0`**, default route via `192.168.2.1`, DNS `8.8.8.8`. The interface really is `end0`, not `eth0` — precisely what the `name: "e*"` netplan match in 3.3 was for, and why the original `nmcli con mod eth0 …` version of this task would have failed twice over.
- [x] 4.3 SSH verified: `ssh.service` active **and** enabled and reachable from the network.
- [ ] 4.4 Run `apt update && apt upgrade -y` to bring system current
- [x] 4.4 `apt update && apt upgrade -y` — 66 packages, incl. kernel **6.18.43 → 6.18.44**, `armbian-firmware`, `armbian-bsp-cli`, and `linux-u-boot-orangepi5-current`. Rebooted into 6.18.44 and verified the **SPI flash was not touched** by the u-boot package (first 4 MiB still `267d2019…`).
     Note: the reboot was needed even though `/var/run/reboot-required` was absent — the upgrade replaced `linux-image-current-rockchip64`, so the running kernel lost its modules and `docker.service` could not start until the matching kernel was booted.

## 5. Core Services Setup

- [x] 5.1 Install Docker — ⚠️ **the plan's package list was wrong for trixie**: `docker-compose-plugin` does not exist, and `docker.io` now ships the **daemon only**. Working set:
     ```bash
     sudo apt install -y docker.io docker-cli docker-compose
     ```
     Gives `/usr/sbin/dockerd`, `/usr/bin/docker` (26.1.5, via `docker-cli`) and `/usr/bin/docker-compose` (compose v2.26.1). The repo's scripts invoke the standalone `docker-compose`, which this provides — the plugin-only route would have left them broken.
- [x] 5.2 `sudo usermod -aG docker orangepi` — done (docker gid 104).
- [x] 5.3 Verified: `docker ps` works as `orangepi` with no sudo; `docker.service` active **and** enabled; `containerd` active; `systemctl is-system-running` = running.
- [x] 5.4 Repo — **no clone or pull was performed, deliberately.** The restored repo came back with the old system's *uncommitted* working state (`run.sh`, `qbittorrent/docker-compose.yml`, untracked `copyparty/`) — the config the old system actually ran. Pulling `migration/armbian` would have overwritten it. Separately, the restored 2024 GitHub key is **not authorized** (`ssh -T git@github.com` → Permission denied), so the Pi cannot push; commits are made from the dev box.
- [x] 5.5 `/home/orangepi` restored: 99,678 entries, ownership `30000:30000` — after changing the new install's `orangepi` from uid 1000 to **30000** (the compose files hardcode `PUID/PGID=30000` and the old files were owned by 30000). Without that change every container would have lost access to its own config.
- [x] 5.6 `secrets` and `wg0.conf` arrived inside `/home` and were byte-identical to the belt-and-braces copies on the drive — no separate restore needed.
- [x] 5.7 Key present at `~/.ssh/id_ed25519` (411 B, owned by 30000) but **unauthorized for GitHub** — see 5.4.
- [x] 5.8 Actual bind-mount sources, read from `docker/*/.env`: `~/Documents` (qBittorrent **and** Jackett config), `~/Documents/jellyfin` (empty stub), `~/Documents/copyparty`, `/media`. ⚠️ **The plan's list was wrong** — and worse, these paths resolved against `$HOME`, which is `/root` when `run.sh` runs as root, so the live state sat in `/root/Documents`: **outside the backup**. See design decision 10.

## 6. Docker Stack Deployment

- [x] 6.1 Images — `docker_pull.sh` was **mode 644**, so the nightly image-pull cron had been failing silently; the stack pulled what it needed on `up`. Jellyfin is retired (decision 12), so the set is **5** images.
- [x] 6.2 `/media` restored and verified: **289 files, 142,697,684,057 bytes** — an exact match with the backup, 783 G free.
- [x] 6.3 Stack started — ⚠️ **the documented command was wrong**: `cd ~/Github/orangepi5 && ./docker/run.sh` fails, because the old `run.sh` only resolved its `../..` paths as a side effect of `cd gluetun`, which itself only executed when `pia-wg-config` was missing. `run.sh` was rewritten with absolute paths and no `HOME`/CWD dependence.
- [x] 6.4 Verified: `gluetun`, `qbittorrent`, `jackett`, `stremio`, `copyparty` all up; gluetun healthy.
- [x] 6.5 ~~Jellyfin~~ — **service retired** (decision 12). Compose dir deleted, removed from `run.sh` and the pull list; the image and its state are no longer part of this system.
- [x] 6.6 qBittorrent WebUI HTTP 200 (Jackett 301, copyparty 200) — all reachable through gluetun's network namespace.
- [x] 6.7 VPN — **WireGuard, not OpenVPN**: PIA's provisioning changed (decision 9). `wg0.conf` minted with `docker/refresh-wireguard.sh`; endpoint `45.89.249.18:1337`, exit IP `45.89.249.204` (Toronto), **389 Mbps** through the tunnel vs 630 Mbps raw, and qBittorrent's egress confirmed through it.
- [x] 6.8 Resilience — `gluetun` had **no restart policy** while the other four had `unless-stopped`, so a reboot would have brought Docker up and left the entire VPN stack down. Fixed, plus `media-stack.service` (ordered start at boot) and `vpn-watchdog.timer` (restarts the stack, then rotates the server). Proven by an unattended reboot: gluetun healthy, tunnel up, all 5 containers back. See decision 11.

## 7. Verification & Validation

Run each check against the Baseline in `design.md`.

- [x] 7.1 Network: `192.168.2.113/24` on **`end0`**, gateway `192.168.2.1`, DNS `8.8.8.8` ✓
- [x] 7.2 MAC — **changed**: `be:70:59:6b:62:f2` (baseline recorded `0a:79:72:f3:0f:3b`, on `eth0`). Armbian names the NIC `end0` and the locally-administered MAC comes from the device tree, so it is not preserved. The static address is configured on the host, so nothing here depends on it — but any router rule keyed to the old MAC is now stale.
- [x] 7.3 All services running and healthy — 5, Jellyfin retired
- [x] 7.4 `gluetun` reports `healthy`
- [x] 7.5 VPN egress confirmed: `45.89.249.204` (PIA Toronto); qBittorrent's own egress check returns the same address, so the stack really is behind the tunnel
- [x] 7.6 ~~Jellyfin~~ retired (decision 12)
- [x] 7.7 qBittorrent WebUI HTTP 200 at http://192.168.2.113:8080
- [x] 7.8 Jackett HTTP 301 at http://192.168.2.113:9117 — with its **original API key restored** (decision 10)
- [x] 7.9 5 images present (Jellyfin's retired)
- [x] 7.10 Cron restored with absolute paths: `docker_pull.sh` and `run.sh` daily. `docker_pull.sh` was mode 644, so the old entry never ran — now executable. No watchtower in the baseline.
- [ ] 7.11 Storage: single 944 G partition, rootfs grown from 1.68 GiB — **still to confirm** that the BTRFS RAID1 fstab entries stay absent (drives remain powered off)
- [ ] 7.12 **Coverage check passes** (`scripts/verify-coverage.sh`, task 2.9) — the check whose absence caused the loss
- [ ] 7.13 Run the **48-hour burn-in** before closing the rollback window
- [x] 7.14 **Reboot test**: unattended `systemctl reboot` → all 5 containers return, gluetun healthy, tunnel up, WebUIs answering (decision 11)
- [ ] 7.15 The live stack config is committed to git — it is currently **single-copy on the Pi**, which is precisely how it was lost the first time (task 9.7)

## 8. Finalization (after 48-hour burn-in passes)

- [ ] 8.1 On the new Armbian system, ensure the migration branch is up to date: `cd ~/Github/orangepi5 && git pull origin migration/armbian`
- [ ] 8.2 Push any post-migration fixes or config updates back to the branch
- [ ] 8.3 Merge migration/armbian into main and push: `git checkout main && git merge migration/armbian && git push origin main`
- [ ] 8.4 Delete the remote branch: `git push origin --delete migration/armbian`
- [ ] 8.5 Delete the local branch: `git branch -d migration/armbian`
- [ ] 8.6 Run `openspec archive change armbian-migration` to archive the completed change

## 9. Post-Migration Cleanup (deferred / optional)

- [x] 9.1 VPN config generation — **the original task was unachievable as written.** `pia-wg-config` (and anything else calling `privateinternetaccess.com/api/client/v2/addKey`) is dead: that endpoint returns 404. PIA moved key registration onto the VPN server itself, behind a token. Replaced by `docker/refresh-wireguard.sh`, which wraps PIA's maintained `manual-connections`; verified end to end, including a server rotation (decision 9). The old task's premise — "the existing wg0.conf still works, so the VPN is fine" — turned out to be false: its endpoint had been retired and the tunnel was handshaking with nobody.
- [ ] 9.2 Install Docker auto-prune cron: `docker system prune --volumes -f` weekly to prevent image/volume bloat
- [ ] 9.3 Install convenience extras as needed (VS Code, RustDesk, Firefox, Flatpak apps) — one at a time. **Go is no longer needed**: it was installed only to build the dead PIA tool and has been removed (decision 13)
- [x] 9.4 Copyparty is already a compose service in the restored repo (`docker/copyparty/`) and is started by `run.sh` — no manual container required
- [ ] 9.5 Clean up old backup drives
- [x] 9.6 Repository tidy-up (decision 13): deleted the stale nested `docker/docker/` duplicate, the typo'd `docker/qbittorrent/qbittorent/` directory (its recovered API key kept as `docker/qbittorrent/reference/jackett.json`), the dropped Jellyfin compose, and the inert `qBittorrent-data.conf` mount + file — qBittorrent reads `qBittorrent.conf`, so that mount never took effect, exactly as the file's own comment suspected
- [ ] 9.7 **Capture the live stack config into git** — compose file, `.env`s, `run.sh`, `docker_pull.sh`, `refresh-wireguard.sh`, docs, and the tuned `qBittorrent.conf`. Today the working config exists only on the Pi, which is how it was lost the first time (task 7.15)
- [ ] 9.8 **Rework the state layout** (decision 10): one obvious state directory for all services, absolute paths in every `.env`, and the coverage check wired into the backup procedure