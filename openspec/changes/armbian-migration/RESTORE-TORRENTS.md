# Restoring the Torrent List (procedure for the next agent)

> **Audience:** the agent continuing this migration. **Status:** method proven end to end; **1 of ~15** folders restored.
> **Read first:** design decision 10 (why the configuration is gone) and section 4 of `HUMAN.md`.

## 1. What can and cannot be restored

| | |
|---|---|
| **Cannot be restored** | The torrent *list* itself. Torrent metadata (`BT_backup/*.torrent`) and the `.fastresume` files lived in the configuration that was never backed up. `/root/Documents` is gone, `BT_backup/` is empty, and the old system was wiped. Do not spend time looking. |
| **Can be restored** | The **seeding state** of content still on disk: re-fetch each release's `.torrent` from TorrentLeech (via Jackett) and re-add it so qBittorrent rechecks the existing files and starts seeding again — **without re-downloading** (26.8 GiB verified at 0 bytes downloaded). |

**The user's stance so far:** *"prove you can do it first with just Gilmore Girls, don't spam TorrentLeech, it's a private tracker."* The method is proven (§4). **Ask before bulk-restoring** — see §6 for the open decisions.

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
curl -s -b $CJ -F "torrents=@/tmp/pick.torrent" -F "savepath=/downloads" \
     -F "paused=true" -F "skip_checking=false" "$QB/api/v2/torrents/add" >/dev/null
sleep 4
H=$(curl -s -b $CJ "$QB/api/v2/torrents/info" | python3 -c "
import json,sys; d=json.load(sys.stdin); print(d[-1]['hash'] if d else '')")
curl -s -b $CJ --data-urlencode "hashes=$H" "$QB/api/v2/torrents/recheck" >/dev/null
# poll every ~8 s: state=checkingDL, downloaded must stay 0
curl -s -b $CJ "$QB/api/v2/torrents/info?hashes=$H" | python3 -c "
import json,sys; t=json.load(sys.stdin)[0]
print(f\"{t['progress']*100:.2f}% {t['state']} downloaded={t['downloaded']}B\")"
```

* `progress == 100.00` → resume, then confirm the tracker: `curl -s -b $CJ "$QB/api/v2/torrents/trackers?hash=$H"` → `status=2` means **working**.
* anything else → `curl -s -b $CJ --data-urlencode "hashes=$H" --data "deleteFiles=false" "$QB/api/v2/torrents/delete"` and report a miss.

## 5. Pitfall that will bite you: Torznab reports `size = 0`

Jackett's Torznab feed returns **`t:size` as 0** for TorrentLeech results. A naive size check therefore always fails and you would wrongly refuse every valid match. **Verify against the `.torrent`'s own metadata instead** — total bytes *and* file count, both compared with `du -sb` / `find -type f`. The proven run matched exactly: `28,787,057,180 bytes / 22 files`, delta `0.00%`, and the recheck reached 100% with `downloaded=0B`.

## 6. Inventory — state as of 2026-09-30

| Folder | Size | Files | Status |
|---|---|---|---|
| `Gilmore Girls (2000) S05 1080p WEBRip 10bit EAC3 2 0 x265-iVy` | 27 G | 22 | ✅ **DONE — seeding** (hash `81871210f036a16b07bed7995ceeb897ee977d63`, tracker working) |
| `Fallout.2024.S01.COMPLETE.1080p.AMZN.WEB.h264-MIXED[TGx]` | 22 G | 6 | to do |
| `The.Bear.S02.COMPLETE.1080p.HULU.WEB.h264-EDITH[TGx]` | 15 G | 12 | to do |
| `Gilmore Girls` *(the other set — name is ambiguous, rely on §5)* | 29 G | 22 | to do |
| `Super.Mario.Odyssey.NSW-BigBlueBox` | 5.5 G | 26 | to do — may not be on TL |
| `Animal_Crossing_New_Horizons_Update_v2.0.6_NSW-VENOM` | 4.1 G | 89 | to do — may not be on TL |
| `28 Days And Weeks Later 2002,2007 1080p BluRay HEVC x265 5.1 BONE` | 3.8 G | 2 | to do |
| `Nexus - Yuval Noah Harari [B0CSZ1LMVX]` | 954 M | 2 | to do |
| `Animal_Crossing_New_Horizons_Happy_Home_Paradise_DLC_NSW-SUXXORS` | 597 M | 15 | to do — may not be on TL |
| `Gabor Mate, Daniel Mate - 2022 - The Myth of Normal (Health)` | 501 M | 9 | to do |
| `The Body Keeps the Score (2021)` | 447 M | 3 | to do |
| `untitled-goose-game_unofficial_linux_port_` | 323 M | 9 | to do — probably not on TL |
| `Enshittification- Why Everything Suddenly Got Worse and What to Do About It [2025]` | 294 M | 1 | to do |

**Needs a human decision before touching** — these look like leftovers, not releases:

| Item | Size | Note |
|---|---|---|
| `1337x` | 12 G | odd name, 16 files — scratch dir? |
| `AAAA` | 7.6 G | odd name, 2 files — scratch dir? |
| `incomplete` | 6.2 G | orphaned partial data from the old client; **cannot** be resumed without its metadata |
| `House.MD…-JATT` | 132 K | stub — metadata only, **no payload** (this is the one that started a 130 GB download; see §2.2) |
| `The.Conjuring.Last.Rites…-BANDOLEROS` | 136 K | stub |
| `The Sopranos S01-S06…-RARBG` | 2.0 M | stub |
| `Animal_Crossing…DLC_Unlocker_NSW-VENOM` | 220 K | stub |
| `orangepi` | 8 K | empty |

The stubs and `incomplete` are safe to delete if the user agrees (reclaims ~6.2 G); the content they once described is already gone.

## 7. Reporting back

Per candidate: folder → matched title → delta % → final state (`seeding` / `miss: not on TL` / `miss: size mismatch`). Aggregate at the end. **Keep the tracker-request count in the report** — the user is watching it deliberately.

Also worth doing once, when the set is restored: commit any new `.torrent`-derived decisions to this spec, and sync the Pi if you committed from elsewhere — **the Pi cannot fetch from GitHub** (`git@github.com: Permission denied (publickey)`); use the bundle workflow in `HUMAN.md`.
