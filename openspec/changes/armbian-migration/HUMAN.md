# Armbian Migration — Human Instructions

> This file is for **you** (the human). It tells you exactly when you need to physically do something.
> The AI agent follows the main task list in `tasks.md` — you don't need to read that.

## What You'll Need

| Item | Why |
|---|---|
| **USB-C NVMe enclosure + spare NVMe** (256 GB+ free space) | To hold the backup of `/home` (~10 GB) and `/media` (~133 GB) alongside whatever is already on it |
| **USB stick** (8 GB+) *or* **SD card** (16 GB+) + reader | Boot medium: a live Armbian environment to run the flash from. USB is preferred — the Pi's USB-A ports are free |
| **Monitor + HDMI cable** or **serial console cable** *(optional)* | Only needed if the Pi fails to appear on the network — the first boot is headless |
| **Internet connection** | The Pi needs to download Docker images after migration |

---

## Step-by-Step

### ⏸️ 0. BEFORE YOU START

Make sure:
- [ ] Your external NVMe has **at least 256 GB free space** — the backup won't delete anything on it
- [ ] You have the backup NVMe enclosure ready (USB-C)
- [ ] You have a **USB stick (8 GB+) or SD card (16 GB+)** for the boot medium
- [ ] You know your PIA VPN credentials (in case WireGuard needs re-auth after migration)
- [ ] You have about **2–4 hours** of total downtime for the Pi

---

### 📦 1. BACKUP — Human Step

The agent will walk you through this, but here's what happens:

1. **Plug the external NVMe into the Orange Pi via USB-C**
   - It should show up as something like `/dev/sda` or `/dev/nvme0n1`
   - If it doesn't appear, run `lsblk` to find it

2. **Tell the agent "ready to backup"**
   - The agent will mount it, rsync `/home` and `/media`, and verify integrity
   - This takes a while (~133 GB of media)

3. **Wait for the agent to say "backup complete"**
   - Leave the NVMe plugged in until after the migration

---

### 💾 2. FLASH ARMBIAN — Human Step

> **Leave the backup NVMe unplugged for this whole section.** Only the boot medium should be attached while the NVMe gets wiped. The images were already copied onto the Pi's internal disk, so nothing here needs the backup drive — it comes back in §4.

1. **The image is already downloaded, checksum-verified and pre-seeded** (the agent did this before you got here)
   - It is `Armbian_26.8.1_Orangepi5_trixie_current_6.18.43_minimal-orangepi-preconfigured.img` on the backup NVMe
   - It boots with **SSH already enabled**, the **`orangepi` / `orangepi`** account, and the **static IP 192.168.2.113** — so there is no first-boot wizard and no monitor or keyboard needed
   - Note: use the **`-preconfigured.img`**, not the original `.img.xz` — the `.img.xz` does *not* have these settings

2. **Plug the boot medium into the Orange Pi** (USB stick preferred; SD card also fine)
   - Just the medium — no separate card reader or computer needed
   - Tell the agent "medium inserted": the agent confirms the device with `lsblk` and writes the image to it
   - If you'd rather write it yourself, the exact command is in `tasks.md` 3.5 — again, point it at the `-preconfigured.img`

3. **Shut down the Pi:**
   ```
   sudo shutdown -h now
   ```

4. **Power on the Pi** — it boots the live medium
   - If it boots the old system instead, press F2/ESC at power-on and select the USB/SD device
   - It comes up on **192.168.2.113** — the same static IP, because the pre-seeded image carries it. No monitor needed.

5. **Tell the agent "booted from the medium, ready to flash"**
   - The agent now has SSH access to the live environment at 192.168.2.113 and will run:
     - `gdisk` to wipe the NVMe partitions
     - `dd` to flash `rkspi_loader.img` to `/dev/mtdblock0`
     - `dd` to write the pre-seeded Armbian image to `/dev/nvme0n1`
   - Nothing needs to be copied onto the medium first — both files already live on the backup NVMe

6. **When agent says "flash complete" — power off:**
   ```
   sudo shutdown -h now
   ```

7. **Remove the boot medium** from the Pi
8. **Power on the Pi** — it will boot Armbian from the NVMe

---

### 🖥️ 3. FIRST BOOT — Human Step

**Nothing to do** — the agent already rebooted the board into the new install over SSH:

1. The Pi now boots **Armbian from the NVMe** (`/dev/nvme0n1p1`, auto-grown to ~930 GB)
2. It answers on **192.168.2.113**, user **`orangepi`**, password **`orangepi`**, with SSH already running
3. The **USB stick is optional now**: it holds the same image plus your `secrets`/`wg0.conf` backups, so it works as a rescue system — leave it in or pull it whenever convenient. (It still carries the image's original UUID; the NVMe was given a new one so the two cannot be confused.)
4. Only if the Pi ever fails to appear on the network: plug in a monitor and check `ip addr`

---

### 🔄 4. RESTORE — Human Step

1. **Plug the backup NVMe back in** — it was deliberately unplugged for the whole flash (§2)
   - Same enclosure, any free USB port (its device name may differ from last time — tell the agent so it can identify it by size and model)

2. **Tell the agent "backup drive connected"**
   - Agent will:
     - Restore `/home` from backup
     - Restore `/media` from backup
     - Pull Docker images
     - Start all containers

3. **Wait for "stack is running"** — the agent will verify each service

4. **Rebuild the configuration that was lost** — this is the part that could not be restored, because it was never in the backup (see design decision 10):
   | What | Status |
   |---|---|
   | **qBittorrent torrents** | the torrent list and `.fastresume` data are gone; every payload is still in `/media`, so re-add and let it recheck |
   | **Jackett indexers** | ✅ done — TorrentLeech re-added and tested (35 results). Note for next time: the login is your **username** `4543562a`, *not* the gmail address |
   | **qBittorrent WebUI password** | ✅ done — `admin` / `admin`, settable again via `docker/qbittorrent/apply-preferences.sh` |
   | **TorrentLeech** | ✅ done — connected in Jackett; your passkey is also embedded in any `.torrent` you download from the site |

---

### ✅ 5. VERIFY — Human Step

Check these URLs in your browser:

| Service | URL | What to look for |
|---|---|---|
| qBittorrent | http://192.168.2.113:8080 | WebUI loads |
| Jackett | http://192.168.2.113:9117 | Jackett dashboard |
| Copyparty | http://192.168.2.113:3923 | file listing |

(Jellyfin was retired — see decision 12.)
<!-- Copyparty is a manual service and is not started during migration -->

All good? Tell the agent "verified" — they'll run the 48-hour burn-in.

---

### 🧹 6. AFTER 48 HOURS

If everything is still working:
1. **Tell the agent "burn-in passed"**
   - They'll merge the `migration/armbian` branch into `main`
   - Archive the migration change
   - You can delete the backup NVMe data

---

## Troubleshooting

| Problem | What to do |
|---|---|
| **Pi won't boot from the USB/SD medium** | Enter the boot menu (F2/ESC during power-on), select the USB or SD device |
| **Can't find the Pi on the network** | The address is static now (`192.168.2.113`), not DHCP — check the router isn't already using it, or connect a monitor and run `ip addr` |
| **Backup NVMe not detected** | Run `lsblk` — if it's there, tell agent the device path |
| **Services don't start** | Tell the agent which one — they'll check the Docker logs |
| **Gluetun VPN not connecting** | The old `wg0.conf` endpoint was retired by PIA. Run `sudo ./docker/refresh-wireguard.sh` on the Pi (it mints a fresh config via PIA's current flow) — or rely on `vpn-watchdog.timer`, which does this automatically after ~30 minutes of a dead tunnel. |
| **Everything is down after a reboot** | Should no longer happen: gluetun has `restart: unless-stopped` and `media-stack.service` starts the stack at boot. Check `systemctl status media-stack` and `journalctl -t vpn-watchdog`. |
| **qBittorrent's search tab shows nothing** | Known defect in the current qBittorrent image, **not** a setup problem (design decision 16 / task 10.4). Use **Jackett's own search at http://192.168.2.113:9117**, which finds the same TorrentLeech releases. |

---

## 🤝 Hand-off Notes (for the next agent)

**State of play:** migration is complete and the stack is healthy (5/5 containers, gluetun healthy, tunnel up, watchdog + boot service active). `migration/armbian` is pushed. The remaining work is short and specific.

### The one unresolved defect: qBittorrent's search tab (task 10.4)

Do **not** re-investigate from scratch — the work is done and written up in **design decision 16**. In short:

* A search hangs ~50 s; qBittorrent forks itself and burns 99% of a core; the Python engine is **never** launched; the job ends `Stopped`/0 and `search/results` returns `Not Found`.
* Everything it depends on is proven working when invoked directly as uid 30000 (`nova2.py --capabilities` emits the expected XML; `nova2.py jackett movies matrix` returns full TorrentLeech results). Python 3.14.7 is found (`Found Python executable` in qBittorrent's log). The engine is present in `~/docker-data/qBittorrent/nova3/` (mode 444, `# VERSION: 1.53` — qBittorrent rewrites it).
* **Prime suspect:** the image build `lscr.io/linuxserver/qbittorrent:latest` = `5.2.4_v2.0.15-ls479`, built 2026-09-29.
* **Suggested next step:** try one tag back (or the official `qbittorrentofficial/qbittorrent-nox`), run a single search, and see whether the fork-at-99%-CPU behaviour disappears. Keep the change reversible and pin whichever tag you settle on.
* **Working substitute meanwhile:** Jackett's UI at `:9117`.

### Then, in order

1. **WireGuard headroom (optional).** 602 Mbps tunneled vs 801 Mbps raw, with one core at 85% — the lever is spreading RX across cores (RPS / multi-queue), deliberately not applied before the burn-in. See decision 14.
2. **Docker auto-prune (task 9.2 / 10.6).** Still not installed. Prefer `docker system prune -f` **without** `--volumes`: the stack uses bind mounts, so the flag buys little and can delete volumes of any stopped container.
3. **48-hour burn-in (task 7.13)** — then run section 8 of `tasks.md` in full: merge `migration/armbian` into `main`, push, delete the branch, and `openspec archive change armbian-migration`.

### Things worth knowing

* **The Pi cannot reach GitHub.** Its remote is SSH (`git@github.com:…`) and the key at `~/.ssh/id_ed25519` is **not authorized**, so `git fetch`/`pull` fail with `Permission denied (publickey)`. Work from a checkout that *can* push (the Termux copy at `/data/data/com.termux/files/home/github/orangepi5` pushes fine), then bring the Pi forward with a bundle:

  ```bash
  # on the pushing checkout
  git bundle create ~/sync.bundle migration/armbian
  cat ~/sync.bundle | ssh orangepi@192.168.2.113 "cat > /home/orangepi/sync.bundle"
  # on the Pi
  cd ~/Github/orangepi5
  git fetch /home/orangepi/sync.bundle migration/armbian:refs/heads/tmp-sync
  git reset --hard tmp-sync && git branch -D tmp-sync
  ```

  Alternatively, authorize the Pi's key on GitHub or switch its remote to HTTPS — either fixes it permanently.
* **`.gitignore` had a dangerous bug, now fixed.** A previous edit appended `.pi-web/` to a file whose last line had no trailing newline, producing the pattern **`wg0.conf.pi-web/`** — which silently stopped ignoring `wg0.conf`, a file holding a WireGuard private key. `wg0.conf`, `.pi-web/` and `wg0.backups/` are now separate, correct lines. `wg0.backups/` deliberately stays inside the repo: the repo directory is in the backup set, `$HOME` is not.
* **A git stash may exist on the Pi** (`git stash list`) from aligning its stale checkout. It was verified file-by-file against origin and is safe to drop — it is a safety net, not unique work.
* `scripts/verify-coverage.sh` proves every bind-mount source is inside the backup set — run it before any destructive step (`checked 8 bind-mount source(s); 0 problem(s)` today).
* Both VPN-failure paths are automated: `vpn-watchdog.timer` restarts the stack after 3 failed checks and rotates the PIA server after 6; `docker/refresh-wireguard.sh` regenerates `wg0.conf` on demand.
* Reproducible recipes live in the repo — `docker/qbittorrent/apply-preferences.sh`, `docker/jackett/apply-indexers.sh`, `scripts/backup.sh` — and credentials stay in the gitignored `secrets` file.
* Be gentle with TorrentLeech: several rapid searches in a row look like abuse to a private tracker.