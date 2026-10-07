# iCSee camera SD-card recovery (WFS)

The laziest way to get footage off the camera: **pop the SD card out, read it on
a PC, put it back.** No network protocol, no NVR, no live bridge — just a card
reader and the WFS tools in this folder.

## TL;DR

```bash
# 0. one-time: install the WFS tools (see "One-time setup")
# 1. pop the card out of the camera, insert into a card reader
lsblk                       # find the device, usually /dev/mmcblk0 (or /dev/sdX)

# 2. let your user read the raw device (root-only by default)
sudo setfacl -m u:$USER:r /dev/mmcblk0

# 3. list + extract (date-prefix or "all")
~/wfs-tools/wfs fls -r -m / /dev/mmcblk0 > /tmp/wfs_body.txt   # index (skip if cached)
~/wfs-tools/wfs-extract 20261005 ~/wfs-recovered              # extract one day
~/wfs-tools/wfs-extract all ~/wfs-recovered                    # extract everything

# 4. preview a clip without copying it (inode from ~/wfs-recovered/index.csv, col 5)
~/wfs-tools/wfs-play 25467

# 5. pop the card back into the camera
```

## Why not just mount it?

The camera (XiongMai / iCSee) formats the card with its own **WFS0.4** filesystem.
There is **no partition table** and Linux cannot mount it (`mmcblk0: Can't lookup
blockdev`). The only way to read it is filesystem-aware tooling.

## Adding / replacing the SD card

A new card is exFAT/FAT32 and the camera expects WFS, so it must be initialized
**by the camera** — there is nothing to do on the PC:

1. Power the camera, insert the card, wait ~30 s.
2. iCSee app → device → **Settings → Storage / SD Card** (sometimes *Record → Disk*).
   - Shows capacity + **Normal** → done (firmware auto-formatted it).
   - Shows **Unformatted / Abnormal / 0 GB** → tap **Format**.

Notes:
- Use a **high-endurance** card (SanDisk Max Endurance, Samsung PRO Endurance);
  24/7 recording kills normal cards fast. Capacity is firmware-limited — 128 GB
  works on this camera; test before trusting 256 GB.
- Pre-formatting on the PC is pointless — the camera re-formats to WFS regardless.
- Formatting **wipes the card** (protocol op `OPStorageManagerClear`).
- Not detected? Reseat; some units only pick up a card inserted while powered off
  then booted.
- Output is identical to the existing card (same `Vid-*.h264` clips, WFS), so the
  extraction runbook above is unchanged.

## One-time setup

```bash
sudo apt install p7zip-full curl ffmpeg
./install-sleuthkit-wfs.sh          # installs ~/wfs-tools/{bin,lib,wfs,wfs-*}
```

`install-sleuthkit-wfs.sh` downloads the prebuilt `sleuthkit-4.9.0-wfs-bin.7z`
from the [`gbatmobile/sleuthkit4.9.0-wfs`](https://github.com/gbatmobile/sleuthkit4.9.0-wfs)
release `v4.9.0-wfs-binaries`. WFS support is **not in upstream Sleuth Kit** — this
fork (`tsk/fs/wfsfs.c`, `wfsfs_dent.c`, `tsk_wfsfs.h`, Common Public License 1.0)
is the only implementation.

## Command reference

| Command | What it does |
|---|---|
| `wfs <tool> ...` | Wrapper that sets `LD_LIBRARY_PATH`; e.g. `wfs fsstat /dev/mmcblk0`, `wfs fls -r -m / /dev/mmcblk0`, `wfs icat /dev/mmcblk0 <inode>` |
| `wfs-extract <prefix> [outdir]` | Extract recordings whose `YYYYMMDD` starts with `<prefix>` (`20261005`, `2024`, or `all`) and remux to MP4 in `outdir` (default `~/wfs-recovered`). Skips non-video records, retries reads 5×. |
| `wfs-play <inode>` | Stream/preview one recording straight off the card with `ffplay`, without copying a full file. |

Environment overrides: `WFS_DEV` (default `/dev/mmcblk0`), `WFS_BODY` (cached
`fls` output), `WFS_HOME`.

Useful one-off queries (from the extractor's `fls` output):

```bash
~/wfs-tools/wfs fsstat /dev/mmcblk0                 # FS summary
~/wfs-tools/wfs fls -r -m / /dev/mmcblk0            # full file listing
grep 20261006 ~/wfs-recovered/index.csv             # find a clip by date/time
```

## Notes / gotchas

- **Card format:** WFS0.4, 512 B blocks, 4096 blocks/fragment (2 MB), no partition
  table. Recordings are named `Vid-YYYYMMDD-HHMMSS-HHMMSS.001.h264`.
- **Read access is via an ACL** and does **not** survive a reboot or re-seating
  the card — re-run `sudo setfacl -m u:$USER:r /dev/mmcblk0` each time.
- **Mixed codecs:** the camera writes both H.264 and H.265/HEVC but names every
  file `.h264`. `wfs-extract` sniffs the stream and picks the right `ffmpeg`
  demuxer. ~0.6–1.1 MB files that start with `37 32 8b 6a` are non-video
  metadata and are skipped.
- **Remuxing:** `ffmpeg -f <codec> -fflags +genpts -r 24 -c copy -movflags
  +faststart` (fallback to the other codec if the first fails).
- **Hot-pulling the card while the camera runs** is the chosen trade-off. The
  camera may be mid-write; if it complains on reinsert, it can usually repair or
  reformat the card. Pull power if you want to be safer, but that is not the
  "lazy" path.
- **Reader flakiness:** the built-in `rtsx_pci_sdmmc` reader has logged
  `hogged CPU` warnings; if reads start timing out, re-seat the card / use a
  different reader.
- **Space:** the full card is ~119 GB (~111 GB of video). Extract to a drive with
  room, or pull day by day.
- Output goes to `~/wfs-recovered/` with an `index.csv` (date, start, end,
  filename, inode, size) and a `failed.log`.

## Files here

- `wfs` – wrapper for the Sleuth Kit WFS binaries
- `wfs-extract` – batch extractor + MP4 remuxer
- `wfs-play` – stream a single recording off the card
- `install-sleuthkit-wfs.sh` – one-time installer for the toolchain
