# Restoring the Torrent List (procedure for the next agent)

> **Audience:** the agent continuing this migration. **Status:** bulk restore done 2026-09-30 — **7 torrents seeding**, 5 permanent misses, 1 partial (Fallout, awaiting decision).
> **Read first:** design decision 10 (why the configuration is gone) and section 4 of `HUMAN.md`.
> A working helper implementing this procedure is `restore_one.py` next to this file.

## 1. What can and cannot be restored

| | |
|---|---|
| **Cannot be restored** | The torrent *list* itself. Torrent metadata (`BT_backup/*.torrent`) and the `.fastresume` files lived in the configuration that was never backed up. `/root/Documents` is gone, `BT_backup/` is empty, and the old system was wiped. Do not spend time looking. |
| **Can be restored** | The **seeding state** of content still on disk: re-fetch each release's `.torrent` from TorrentLeech (via Jackett) and re-add it so qBittorrent rechecks the existing files and starts seeding again — **without re-downloading** (26.8 GiB verified at 0 bytes downloaded). |

**The user's stance:** *"prove you can do it first with just Gilmore Girls, don't spam TorrentLeech, it's a private tracker."* The method is proven (§4) and the user then approved restoring the rest. Keep the tracker request budget in mind anyway (§2.1).

## 2. Ground rules (non-negotiable)

1. **TorrentLeech is a private tracker.** Budget about **1 search + 1 `.torrent` fetch per candidate**, space them ~10 s apart, and never loop retries. The whole inventory is ~30 requests *in total*.
2. **Never add a torrent you have not verified against the disk** (§5). An unverified add silently starts a full re-download — that is exactly what happened with `House.MD` and it had to be stopped.
3. **Add paused, recheck, and resume only at 100%.** On any other result, delete the entry (`deleteFiles=false`) and report a miss. A miss costs nothing.
4. **Reuse cached search results** rather than re-querying: keep `/tmp/tl.xml` per candidate.
5. **Do not use qBittorrent's WebUI search tab** — it is broken in this image (decision 16). Jackett's own UI/API is the working path, and that is all this procedure needs.

## 3. Environment

| Thing | Value |
|---|---|
| qBittorrent WebUI | `http://192.168.2.113:8080` — `admin` / `admin` (no `Referer` header needed for these calls) |
| Jackett | `http://192.168.2.113:9117` — **session cookie required** for `/UI/*`, not for Torznab |
| Jackett API key | read it, don't hardcode: `python3 -c "import json;print(json.load(open('/media/jackett.json'))['api_key'])"` |
| Payload location | On the host `/media/<release>/`; **inside qBittorrent the same tree is `/downloads`** |
| Save path to pass | `savepath=/downloads` (the torrent's own root folder name then lands on the existing folder) |
| TorrentLeech announce | `https://tracker.torrentleech.org/a/<passkey>` — the passkey is already inside every fetched `.torrent` |

## 4. Procedure per candidate

```bash
QB=http://192.168.2.113:8080
JJ=http://192.168.2.113:9117
KEY=$(python3 -c "import json;print(json.load(open('/media/jackett.json'))['api_key'])")
```

**Step 1 — measure what is on disk.** If it is under ~10 MB it is a stub with no payload: stop, it cannot be seeded.

```bash
DIR="/media/Gilmore Girls (2000) S05 1080p WEBRip 10bit EAC3 2 0 x265-iVy"
DISK=$(sudo du -sb "$DIR" | cut -f1)
DISKFILES=$(sudo find "$DIR" -type f | wc -l)
```

**Step 2 — one Torznab search**, querying a distinctive substring of the folder name:

```bash
curl -s --max-time 90 "$JJ/api/v2.0/indexers/torrentleech/results/torznab/api?apikey=$KEY&t=search&q=Gilmore%20Girls%20S05%201080p%20WEBRip%20x265-iVy" -o /tmp/tl.xml
```

**Step 3 — check you have a hit** and capture the download URL from the cached XML (never re-search just to get it):

```bash
python3 - <<'PY'
import xml.etree.ElementTree as ET
raw = open('/tmp/tl.xml', encoding='utf-8', errors='replace').read()
if '<item>' not in raw:
    raise SystemExit("no results -> record as a miss, do not guess")
root = ET.fromstring(raw)
enc = root.find('.//item/enclosure')
open('/tmp/pick.url','w').write(enc.get('url'))
print("candidate:", root.findtext('.//item/title'))
PY
```

**Step 4 — fetch that `.torrent` (one tracker API call):**

```bash
curl -sL --max-time 60 "$(cat /tmp/pick.url)" -o /tmp/pick.torrent
```

**Step 5 — verify by reading the torrent's own metadata** (see §5 for why Torznab's size is useless here). Proceed **only** on `MATCH`:

```bash
python3 - "$DISK" "$DISKFILES" <<'PY'
import sys
data = open('/tmp/pick.torrent','rb').read()
def bdecode(b, i=0):
    c = b[i:i+1]
    if c == b'i':
        j = b.index(b'e', i); return int(b[i+1:j]), j+1
    if c == b'l':
        i += 1; out = []
        while b[i:i+1] != b'e':
            v, i = bdecode(b, i); out.append(v)
        return out, i+1
    if c == b'd':
        i += 1; out = {}
        while b[i:i+1] != b'e':
            k, i = bdecode(b, i); v, i = bdecode(b, i); out[k] = v
        return out, i+1
    j = b.index(b':', i); n = int(b[i:j]); return b[j+1:j+1+n], j+1+n
meta, _ = bdecode(data); info = meta[b'info']
name = info[b'name'].decode()
if b'files' in info:
    files = [(f[b'path'][-1].decode(), f[b'length']) for f in info[b'files']]
    total = sum(l for _, l in files)
else:
    files = [(name, info.get(b'length', 0))]; total = info.get(b'length', 0)
disk, diskfiles = int(sys.argv[1]), int(sys.argv[2])
delta = abs(total - disk) / disk * 100 if disk else 999
print(f"torrent: {name}\n  {total} bytes / {len(files)} files")
print(f"on disk: {disk} bytes / {diskfiles} files  -> delta {delta:.2f}%")
ok = delta < 2.0 and abs(len(files) - diskfiles) <= 2
print("VERDICT:", "MATCH - safe to add" if ok else "MISMATCH - do NOT add")
open('/tmp/verdict','w').write('ok' if ok else 'no')
PY
```

**Step 6 — add paused, recheck, resume only at 100%:**

```bash
CJ=/tmp/qb.jar; rm -f $CJ
curl -s -c $CJ -o /dev/null -d 'username=admin&password=admin' "$QB/api/v2/auth/login"
# qBittorrent 5.x: `paused` is gone, use `stopped`; and for TGx-style flattened
# folders (torrent root name != folder name) `contentLayout=NoSubfolder` +
# savepath=/downloads/<folder> is what makes the recheck find the files.
RESP=$(curl -s -b $CJ -F "torrents=@/tmp/pick.torrent" \
     -F "savepath=/downloads/<folder>" -F "contentLayout=NoSubfolder" \
     -F "stopped=true" -F "skip_checking=false" "$QB/api/v2/torrents/add")
H=$(echo "$RESP" | python3 -c "import json,sys; print(json.load(sys.stdin)['added_torrent_ids'][0])")
curl -s -b $CJ --data-urlencode "hashes=$H" "$QB/api/v2/torrents/recheck" >/dev/null
# poll every ~8 s: state=checkingDL, downloaded must stay 0
curl -s -b $CJ "$QB/api/v2/torrents/info?hashes=$H" | python3 -c "
import json,sys; t=json.load(sys.stdin)[0]
print(f\"{t['progress']*100:.2f}% {t['state']} downloaded={t['downloaded']}B\")"
```

* `progress == 100.00` → **start** it (`/api/v2/torrents/start`; 5.x renamed `resume`→`start`), reannounce, then confirm the tracker: `/api/v2/torrents/trackers?hash=$H` → `status=2` means **working** (it can sit at `1` = not-contacted-yet for a minute; reannounce and retry).
* anything else → delete with `deleteFiles=false` and report a miss; also clean `/media/incomplete/<torrent name>` (partial data) if it was created.

## 5. Pitfall that will bite you: verify against the `.torrent`, not Torznab

Jackett's Torznab feed has been observed returning **`t:size` as 0** for TorrentLeech results, which would make a naive size check fail and wrongly refuse every valid match. In the 2026-09-30 runs the size attribute *was* populated, so do not rely on it either way. **Always verify against the `.torrent`'s own metadata** — total bytes *and* file count, both compared with `du -sb` / `find -type f`. Examples from the proven run: `28,787,057,180 bytes / 22 files` delta `0.00%`, and `5,887,690,064 bytes / 26 files` delta `0.00%`, both rechecked to 100% with `downloaded=0B`.

A size+count match is necessary but **not sufficient** when the release was repacked: TGx strips/renames files, so the on-disk names can differ from the tracker torrent. The recheck is the final arbiter — it must reach 100.00% *before* you start the torrent.

## 6. Inventory — state as of 2026-09-30 (bulk restore complete)

**7 torrents seeding** (all 100.00%, `downloaded=0B`, tracker `status=2`):

| Folder | Size | Files | Hash |
|---|---|---|---|
| `Gilmore Girls (2000) S05 1080p WEBRip 10bit EAC3 2 0 x265-iVy` | 27 G | 22 | `81871210f036a16b07bed7995ceeb897ee977d63` |
| `The.Bear.S02.COMPLETE.1080p.HULU.WEB.h264-EDITH[TGx]` | 15 G | 12 | `341b3861b49b1c159cbc0b55d28edc51df9cdc35` |
| `Super.Mario.Odyssey.NSW-BigBlueBox` | 5.5 G | 26 | `e634e8e36625c8a1e5269f9294ef3b92264c7569` |
| `Animal_Crossing_New_Horizons_Update_v2.0.6_NSW-VENOM` | 4.1 G | 89 | `2512169d0a801f578169c7730d82838ba32e890a` |
| `Nexus - Yuval Noah Harari [B0CSZ1LMVX]` | 954 M | 2 | `b34497f3e291fcfecaaee4d86a1e2785032893ba` |
| `Animal_Crossing_New_Horizons_Happy_Home_Paradise_DLC_NSW-SUXXORS` | 597 M | 15 | `12345674672f0845c42aa14ad667c8e3b8dd76bd` |
| `The Body Keeps the Score (2021)` | 447 M | 3 | `2bc4265f14a21b26fe8ac0803ce2c013f224d00b` |

**Cannot be seeded** — the exact release is not on TorrentLeech. No download was started:

| Folder | Size | Reason |
|---|---|---|
| `Gilmore Girls` (the other set = **S04**, complete 22 eps) | 29 G | files are `…HEVC-MONOLITH`; TL only has Rajput42 / iVy / BORDURE S04 groups (different names → recheck would fail) |
| `28 Days And Weeks Later 2002,2007 1080p BluRay HEVC x265 5.1 BONE` | 3.8 G | TL has only the **720p** BONE pack |
| `Gabor Mate, Daniel Mate - 2022 - The Myth of Normal (Health)` | 501 M | not on TL (only other Gabor Maté titles) |
| `untitled-goose-game_unofficial_linux_port_` | 323 M | TL has only PS4 releases |
| `Enshittification- …` | 294 M | disk is the **m4b audiobook**; TL has only the epub |

**Partial — needs a human decision:**

| Item | Size | Note |
|---|---|---|
| `Fallout.2024.S01.COMPLETE.1080p.AMZN.WEB.h264-MIXED[TGx]` | 22 G | disk holds only **E03–E08** (6 of 8). The TL pack `Fallout 2024 S01 1080p WEB h264-MIXED` is 32.3 G / 9 files — re-adding it paused would recheck to ~72% and then **re-download ~9.5 G** to complete the season. Not done without approval. |

**Leftovers — deleted 2026-09-30** (user approved; ~6.2 G reclaimed):

| Item | Size | Note |
|---|---|---|
| `incomplete/` | 6.2 G | orphaned partial data from the old client; could never be resumed without its metadata. **Also contains the temp `/media/incomplete/<name>` folder a failed recheck leaves behind — check it after every miss.** |
| `House.MD…-JATT` | 132 K | stub — metadata only, **no payload** (this is the one that started a 130 GB download; see §2.2) |
| `The.Conjuring.Last.Rites…-BANDOLEROS` | 136 K | stub |
| `The Sopranos S01-S06…-RARBG` | 2.0 M | stub |
| `Animal_Crossing…DLC_Unlocker_NSW-VENOM` | 220 K | stub |
| `orangepi` | 8 K | empty dir — left in place (not media) |

**Left alone — not TorrentLeech content** (user only wanted TL releases restored):

| Item | Size | Note |
|---|---|---|
| `1337x/` | 12 G | 3 movie releases (`The Ugly Stepsister`, 2× `The Way Way Back`) from 1337x |
| `AAAA/` | 8.1 G | `Love Overboard S01E04/E05` 2160p Kitsune — real media, just an odd folder name |

## 7. Reporting back

Per candidate: folder → matched title → delta % → final state (`seeding` / `miss: not on TL` / `miss: size mismatch`). Aggregate at the end. **Keep the tracker-request count in the report** — the user is watching it deliberately.

**2026-09-30 bulk run used ~44 TorrentLeech requests** (≈35 searches + ≈9 `.torrent` fetches) — over the ~30 budget of §2.1, mostly from iterative query refinement (some candidates needed several tries before a distinctive query hit). Fold the good queries back here so the next run is one-search-per-candidate:

| Release | Query that works |
|---|---|
| Fallout S01 MIXED | `Fallout S01 h264-MIXED` |
| The Bear S02 | `The Bear S02 EDITH` |
| Super Mario Odyssey | `Super Mario Odyssey NSW-BigBlueBox` |
| AC Update v2.0.6 | `Animal Crossing New Horizons v2.0.6 NSW-VENOM` |
| AC Happy Home DLC | `Animal Crossing New Horizons Happy Home Paradise NSW-SUXXORS` |
| Nexus (audiobook) | `Nexus Yuval Noah Harari` |
| The Body Keeps the Score | `The Body Keeps the Score` |
| searches that are *guaranteed* 0 | `… MONOLITH`, `… 1080p BluRay BONE` pack, `Myth of Normal`, `untitled goose game` (Linux), `Enshittification` (m4b) |

Also worth doing once, when the set is restored: commit any new `.torrent`-derived decisions to this spec, and sync the Pi if you committed from elsewhere — **the Pi cannot fetch from GitHub** (`git@github.com: Permission denied (publickey)`); use the bundle workflow in `HUMAN.md`.
