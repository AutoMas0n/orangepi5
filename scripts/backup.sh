#!/bin/bash
# Back up exactly what the coverage rule says matters, and nothing less.
# Usage: sudo ./scripts/backup.sh [destination]
# The destination is the mounted backup drive (the NVMe enclosure auto-mounts
# under /media/orangepi/<label>; prefer a bind mount so the copy is not nested
# inside the source).
set -euo pipefail
REPO=/home/orangepi/Github/orangepi5
STATE=/home/orangepi/docker-data
DEST=${1:-/mnt/backup-nvme/armbian-backup}
STAMP=$(date -Is)

echo "==> coverage check first"
"$REPO/scripts/verify-coverage.sh" || { echo "coverage check FAILED - refusing to back up"; exit 1; }

echo "==> destination: $DEST"
mkdir -p "$DEST"/{repo,docker-data,media,home}
df -h "$DEST" | tail -1
{ echo "backup $STAMP"; echo "repo: $REPO"; echo "state: $STATE"; } > "$DEST/MANIFEST.txt"

echo "==> repo (code + config)"
rsync -aAX --info=progress2 --delete "$REPO/" "$DEST/repo/"
echo "==> docker-data (all service state)"
rsync -aAX --info=progress2 --delete "$STATE/" "$DEST/docker-data/"
echo "==> media (133 G payloads)"
rsync -aAX --info=progress2 /media/ "$DEST/media/"
echo "==> secrets across: gitignored credentials + ssh"
rsync -aAX --info=progress2 "$REPO/secrets" "$REPO/wg0.conf" "$DEST/repo/" 2>/dev/null || true
rsync -aAX --info=progress2 --exclude known_hosts /home/orangepi/.ssh/ "$DEST/home/ssh/"

echo "==> verification (counts + sizes)"
for pair in "$REPO:repo" "$STATE:docker-data" "/media:media"; do
  src=${pair%%:*}; sub=${pair##*:}
  printf '  %-12s src=%-6s dest=%-6s bytes=%s\n' "$sub" \
    "$(find "$src" -type f 2>/dev/null | wc -l)" \
    "$(find "$DEST/$sub" -type f 2>/dev/null | wc -l)" \
    "$(du -sb "$DEST/$sub" 2>/dev/null | cut -f1)"
done
echo "==> done at $(date -Is)"
