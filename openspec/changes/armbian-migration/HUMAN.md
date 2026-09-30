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

---

### ✅ 5. VERIFY — Human Step

Check these URLs in your browser:

| Service | URL | What to look for |
|---|---|---|
| Jellyfin | http://192.168.2.113:8096 | Login page loads |
| qBittorrent | http://192.168.2.113:8080 | WebUI loads |
| Jackett | http://192.168.2.113:9117 | Jackett dashboard |
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
| **Gluetun VPN not connecting** | Known issue — PIA credentials may need updating (see task 9.1) |