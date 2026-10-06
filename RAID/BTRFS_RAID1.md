```bash
lsblk
ls -l /dev/disk/by-id/ | grep 'sda\|sde'
sudo mkfs.btrfs -m raid1 -d raid1 /dev/disk/by-id/scsi-SASMT_ASM235CM_50C000000519 /dev/disk/by-id/scsi-SASMT_ASM235CM_20C000000519 -f
```

Thanks for catching that! Let’s correct the instructions based on your actual `blkid` output. Your Btrfs RAID 1 array is already created and spans `/dev/sda` and `/dev/sde` with UUID `96548547-3eb9-4d66-af17-8c2a19dd81f3`. Here’s the revised guide:

---

### **1. Mount the BTRFS Array**

Keep in mind when you run `sudo blkid` you will get a shared UUID between `sde` & `sda`

> **⚠️ Scan the devices first.** BTRFS is a multi-device filesystem: it must have **both** members registered before it can read the array. If only one is in the kernel's device list — common on a multi-bay USB enclosure where the drives enumerate a moment apart — the mount fails with `devid N uuid … is missing` / `failed to read the system array: -2` / `open_ctree failed: -2`. `sudo btrfs device scan` registers all members and fixes it.

```bash
sudo mkdir -p /mnt/btrfs_raid1
sudo btrfs device scan                 # register BOTH members — do this every time
sudo mount UUID="96548547-3eb9-4d66-af17-8c2a19dd81f3" /mnt/btrfs_raid1
```

Confirm both members are present:

```bash
sudo btrfs filesystem show
# should list devid 1 (/dev/sdd) and devid 2 (/dev/sdb)
```

---

### **2. Update `/etc/fstab` for Persistent Mounting**
Add this line to `/etc/fstab` (use `sudo nano /etc/fstab`):  
```bash
# Use the shared UUID of the BTRFS array
UUID=96548547-3eb9-4d66-af17-8c2a19dd81f3  /mnt/btrfs_raid1  btrfs  defaults,autodefrag,compress=zstd,nofail  0 0
```
- **Do not add `degraded`.** It lets the array mount with one member missing, silently running you with **no redundancy** instead of failing loudly. Use `nofail` so a powered-off array doesn't block boot, and scan the devices before mounting (section 1).
- If you want it to auto-mount at boot, add a oneshot unit that runs `sudo btrfs device scan` before `mnt-btrfs_raid1.mount` (or leave it out of fstab and mount it by hand).
- Test it:  
  ```bash
  sudo umount /mnt/btrfs_raid1
  sudo mount -a
  ```

---

### **3. Verify the RAID Status**
```bash
sudo btrfs filesystem show /mnt/btrfs_raid1
```
You should see both `/dev/sda` and `/dev/sde` listed as devices in the RAID 1 array.

---

### **4. Important Notes for Your Setup**
#### **Device Paths vs. UUIDs**
- Your original command used `/dev/disk/by-id/...` paths, but since you’ve already created the array, **always reference it by UUID** (safer than device paths like `/dev/sda`, which can change).

#### **Power Management**
- If one drive is powered off, the array will mount in degraded mode. To re-add a powered-off drive later:  
  > ⚠️ Mounting `degraded` runs with **no redundancy** and hides a member that is merely unscanned. Only use it deliberately, after `btrfs device scan` has failed to bring the member back.
  ```bash
  sudo btrfs device scan  # Rescan for devices
  sudo mount -o degraded /mnt/btrfs_raid1  # If needed
  ```

#### **Check Usage**
```bash
sudo btrfs filesystem df /mnt/btrfs_raid1
```

---

### **5. Fixing the Initial Mistake**
The `grep` command failed because:
- There’s no `/dev/mapper/...` path for your USB-connected drives.  
- Btrfs RAID 1 arrays use a **shared UUID** across all devices (visible in `blkid`), not individual partitions.

---

### **Final Checks**
1. Confirm the array is mounted:  
   ```bash
   df -h | grep btrfs
   ```
2. Start a scrub to verify data integrity:  
   ```bash
   sudo btrfs scrub start /mnt/btrfs_raid1
   sudo btrfs scrub status /mnt/btrfs_raid1
   ```

### **Troubleshooting Tips**

- **Mount fails with `devid N uuid … is missing` / `failed to read the system array: -2` / `open_ctree failed: -2`**:  
  The second member was not scanned. Register it and retry:
  ```bash
  sudo btrfs device scan
  sudo mount UUID="96548547-3eb9-4d66-af17-8c2a19dd81f3" /mnt/btrfs_raid1
  ```
  Confirm both devices appear in `sudo btrfs filesystem show`. Do **not** "fix" this with `-o degraded` — that mounts a single copy and hides the problem.

- **If a Drive Disappears**:  
  - Power it on and rescan:  
    ```bash
    sudo btrfs device scan
    ```
- **Check Kernel Logs**:  
  ```bash
  dmesg | grep -i btrfs
  ```
- **Recovery**:  
  If both drives are corrupted, use `btrfs check --repair` (use cautiously!).

---

### **Final Configuration Summary**
```bash
# Verify everything works:
df -h /mnt/btrfs_raid1              # Check free space
sudo btrfs filesystem df /mnt/btrfs_raid1  # Detailed BTRFS usage
```


### Apply Permissions

```bash
sudo chown orangepi /mnt/btrfs_raid1
sudo chmod u+w /mnt/btrfs_raid1
```