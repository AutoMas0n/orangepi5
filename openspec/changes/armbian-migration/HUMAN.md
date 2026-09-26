# Armbian Migration — Human Instructions

> This file is for **you** (the human). It tells you exactly when you need to physically do something.
> The AI agent follows the main task list in `tasks.md` — you don't need to read that.

## What You'll Need

| Item | Why |
|---|---|
| **USB-C NVMe enclosure + spare NVMe** (256 GB+ recommended) | To back up `/home` (~10 GB) and `/media` (~133 GB) |
| **SD card** (16 GB+), **SD card reader** | To boot the Armbian installer |
| **Monitor + HDMI cable** or **serial console cable** | For the Armbian first-boot wizard |
| **USB keyboard** | To type during first-boot wizard (if using monitor) |
| **Internet connection** | The Pi needs to download Docker images after migration |

---

## Step-by-Step

### ⏸️ 0. BEFORE YOU START

Make sure:
- [ ] Your external NVMe is **empty or expendable** — it will get wiped by the backup
- [ ] You have the backup NVMe enclosure ready (USB-C)
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

### 💾 2. FLASH ARMBIA — Human Step

1. **Tell the agent to download the Armbian image**
   - Agent runs: `wget https://dl.armbian.com/orangepi5/Trixie_current_minimal`
   - Wait for agent to verify checksum

2. **Write the image to an SD card** (you do this part):
   ```
   # On your computer (or on the Pi itself):
   # Find your SD card device (IMPORTANT: don't wipe your main drive!)
   lsblk
   
   # If SD card is /dev/sdX, write the image:
   xzcat ~/Downloads/Armbian_*_Orangepi5_trixie_current_*.img.xz | \
     sudo dd bs=1M of=/dev/sdX status=progress
   ```

3. **Also copy the bootloader file** to the SD:
   - You need `rkspi_loader.img` — it's in the `flash-image-ansible/roles/flash_firmware/files/` directory of this repo

4. **Shut down the Pi:**
   ```
   sudo shutdown -h now
   ```

5. **Remove the SD card from your computer**, insert it into the Orange Pi
6. **Connect a monitor+keyboard** (or serial console) to the Pi
7. **Power on the Pi** — it will boot from the SD card

8. **Tell the agent "booted from SD, ready to flash"**
   - Agent will SSH in and run:
     - `gdisk` to wipe the NVMe partitions
     - `dd` to flash `rkspi_loader.img` to `/dev/mtdblock0`
     - `xzcat … | dd` to write Armbian to `/dev/nvme0n1`

9. **When agent says "flash complete" — power off:**
   ```
   sudo shutdown -h now
   ```

10. **Remove the SD card** from the Pi
11. **Power on the Pi** — it will boot Armbian from the NVMe

---

### 🖥️ 3. FIRST BOOT — Human Step

1. **Watch the console** — Armbian shows a first-boot wizard
2. **Set these values** when prompted:

   | Prompt | What to type |
   |---|---|
   | Hostname | `orangepi` |
   | Username | `orangepi` |
   | Password | `orangepi` (or whatever you use) |
   | Timezone | Your timezone (e.g. `America/New_York`) |
   | Root login | Disallow SSH root login = `yes` |

3. **After the wizard completes**, the Pi will probably reboot
4. **Wait for it to come back up**, then find its IP:
   - Check your router's DHCP leases
   - Or connect a monitor and run `ip addr`

5. **Tell the agent the IP address** (should be `192.168.2.113` if DHCP gives the same one; if different, note it)
6. **Agent will configure the static IP** and install Docker

---

### 🔄 4. RESTORE — Human Step

1. **Plug the backup NVMe back in** (if you removed it)
   - Same enclosure, same USB-C port

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
| Copyparty | http://192.168.2.113:3923 | File browser with your media |

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
| **Pi won't boot from SD** | Enter boot menu (F2/ESC during power-on), select SD card |
| **Can't find the Pi on the network** | Connect a monitor, run `ip addr`, look for `192.168.x.x` |
| **Backup NVMe not detected** | Run `lsblk` — if it's there, tell agent the device path |
| **Services don't start** | Tell the agent which one — they'll check the Docker logs |
| **Gluetun VPN not connecting** | Known issue — PIA credentials may need updating (see task 9.1) |