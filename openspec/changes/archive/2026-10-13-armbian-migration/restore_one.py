#!/usr/bin/env python3
"""Restore one torrent from TorrentLeech via Jackett, then recheck in qBittorrent.

Usage: restore_one.py "<folder name under /media>" "<torznab query>"
Implements RESTORE-TORRENTS.md: 1 search + 1 .torrent fetch, verify metadata
against disk, add stopped, recheck, resume only at 100%.

qBittorrent 5.x notes:
  * add uses `stopped=true` (not `paused=true`); states are stoppedUP/stoppedDL.
  * `contentLayout=NoSubfolder` + savepath=/downloads/<folder> reproduces the
    flattened layout TGx releases have on disk.
"""
import sys, os, json, time, subprocess, difflib
import urllib.request, urllib.parse
import xml.etree.ElementTree as ET

QB = "http://127.0.0.1:8080"
JJ = "http://127.0.0.1:9117"
MEDIA = "/media"
WORK = "/home/orangepi/restore-tmp"
os.makedirs(WORK, exist_ok=True)
CJ = os.path.join(WORK, "cookiejar")

folder = sys.argv[1]
query = sys.argv[2]
DRY = len(sys.argv) > 3 and sys.argv[3] == 'dry'
DIR = os.path.join(MEDIA, folder)

# ---- 1. disk measurement -------------------------------------------------
disk_bytes = 0
disk_files = []
for root, _, files in os.walk(DIR):
    for f in files:
        p = os.path.join(root, f)
        try:
            disk_bytes += os.path.getsize(p)
        except OSError:
            pass
        disk_files.append(os.path.relpath(p, DIR))
print(f"[disk] {disk_bytes} bytes / {len(disk_files)} files")

# ---- 2. one Torznab search ----------------------------------------------
key = json.load(open('/media/jackett.json'))['api_key']
url = (f"{JJ}/api/v2.0/indexers/torrentleech/results/torznab/api"
       f"?apikey={key}&t=search&q={urllib.parse.quote(query)}")
xml = urllib.request.urlopen(url, timeout=120).read().decode('utf-8', 'replace')
open(os.path.join(WORK, 'tl.xml'), 'w').write(xml)
root = ET.fromstring(xml)
items = root.findall('.//item')
print(f"[search] {len(items)} items for: {query}")
if not items:
    print("RESULT: miss: not on TL")
    sys.exit(0)


def norm(s):
    return ' '.join(''.join(c.lower() if c.isalnum() else ' ' for c in s).split())


def score(t):
    a = norm(t)
    best = difflib.SequenceMatcher(None, norm(folder), a).ratio()
    for f in disk_files:
        best = max(best, difflib.SequenceMatcher(None, norm(f), a).ratio())
    ta, tb = set(norm(folder).split()), set(a.split())
    return best + len(ta & tb) / max(1, len(ta | tb))


items = sorted(items, key=lambda it: score(it.findtext('title')), reverse=True)
best_title = items[0].findtext('title')
ratio = max([difflib.SequenceMatcher(None, norm(folder), norm(best_title)).ratio()]
            + [difflib.SequenceMatcher(None, norm(f), norm(best_title)).ratio()
               for f in disk_files])
print(f"[pick] {best_title} (ratio {ratio:.2f})")
if ratio < 0.60:
    print(f"RESULT: miss: no close match (best ratio {ratio:.2f})")
    sys.exit(0)
enc = items[0].find('enclosure')

# ---- 4. one .torrent fetch ----------------------------------------------
torrent = urllib.request.urlopen(enc.get('url'), timeout=120).read()
TTPATH = os.path.join(WORK, 'pick.torrent')
open(TTPATH, 'wb').write(torrent)


# ---- 5. verify against torrent metadata ---------------------------------
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


meta, _ = bdecode(torrent)
info = meta[b'info']
name = info[b'name'].decode()
multi = b'files' in info
if multi:
    files = [f[b'length'] for f in info[b'files']]
    total = sum(files)
else:
    total = info.get(b'length', 0)

delta = abs(total - disk_bytes) / disk_bytes * 100 if disk_bytes else 999
count_delta = (len(files) - len(disk_files)) if multi else (1 - len(disk_files))
print(f"[torrent] {name}  ({'multi' if multi else 'single'})")
print(f"  {total} bytes / {len(files)} files")
print(f"  on disk {disk_bytes} bytes / {len(disk_files)} files -> delta {delta:.2f}%  count_delta {count_delta}")
if not (delta < 2.0 and abs(count_delta) <= 3):
    print("RESULT: miss: size mismatch")
    sys.exit(0)

# ---- 6. add stopped, recheck -------------------------------------------
savepath = f"/downloads/{folder}"
print(f"[add] savepath={savepath} contentLayout=NoSubfolder")
if DRY:
    print("RESULT: dry-run verified MATCH, not added")
    sys.exit(0)


def curl(args, raw=False):
    out = subprocess.run(["curl", "-s", "-b", CJ, "-c", CJ] + args,
                         capture_output=True, text=True).stdout
    return out if raw else json.loads(out)


def qb(args):
    """Fire-and-forget endpoint (returns 204/empty)."""
    subprocess.run(["curl", "-s", "-b", CJ, "-c", CJ] + args,
                   capture_output=True, text=True)


subprocess.run(["curl", "-s", "-c", CJ, "-o", "/dev/null",
                "-d", "username=admin&password=admin",
                f"{QB}/api/v2/auth/login"], check=True)
resp = curl(["-F", f"torrents=@{TTPATH}", "-F", f"savepath={savepath}",
             "-F", "stopped=true", "-F", "contentLayout=NoSubfolder",
             "-F", "skip_checking=false", f"{QB}/api/v2/torrents/add"], raw=True)
h = None
try:
    h = json.loads(resp)["added_torrent_ids"][0]
except Exception:
    pass
if not h:
    time.sleep(4)
    for t in curl([f"{QB}/api/v2/torrents/info"]):
        if t['name'] == name:
            h = t['hash']
print(f"[hash] {h}")

qb(["--data-urlencode", f"hashes={h}", f"{QB}/api/v2/torrents/recheck"])

CHECKING = ('checkingUP', 'checkingDL', 'checkingResumeData')
deadline = time.time() + 900
started = False
while time.time() < deadline:
    time.sleep(8)
    t = curl([f"{QB}/api/v2/torrents/info?hashes={h}"])[0]
    print(f"   {t['progress']*100:6.2f}% {t['state']} downloaded={t['downloaded']}B")
    if t['state'] in CHECKING:
        started = True
        continue
    if t['progress'] >= 1.0:
        break
    if started or time.time() > deadline - 840:
        break

t = curl([f"{QB}/api/v2/torrents/info?hashes={h}"])[0]
if abs(t['progress'] - 1.0) < 1e-4:
    qb(["--data-urlencode", f"hashes={h}", f"{QB}/api/v2/torrents/start"])
    st = 1
    for _ in range(6):
        time.sleep(15)
        qb(["--data-urlencode", f"hashes={h}", f"{QB}/api/v2/torrents/reannounce"])
        time.sleep(5)
        tr = curl([f"{QB}/api/v2/torrents/trackers?hash={h}"])
        st = max([x.get('status', 0) for x in tr if x.get('url', '').startswith('http')] or [0])
        if st == 2:
            break
    t = curl([f"{QB}/api/v2/torrents/info?hashes={h}"])[0]
    print(f"RESULT: seeding hash={h} state={t['state']} tracker_status={st}")
else:
    qb(["--data-urlencode", f"hashes={h}", "--data", "deleteFiles=false",
        f"{QB}/api/v2/torrents/delete"])
    print(f"RESULT: miss: recheck {t['progress']*100:.2f}% (deleted entry, files kept)")
    print(f"NOTE: check /media/incomplete/{name} for partial leftovers")
