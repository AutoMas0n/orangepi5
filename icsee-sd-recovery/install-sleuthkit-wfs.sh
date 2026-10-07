#!/bin/bash
# Install the prebuilt Sleuth Kit 4.9.0 with WFS0.4/0.5 support.
#
# The WFS (XiongMai / iCSee camera) filesystem is only supported by a fork of
# The Sleuth Kit -- upstream has no WFS code. This fetches the prebuilt Linux
# binaries from:
#   https://github.com/gbatmobile/sleuthkit4.9.0-wfs
#   release tag: v4.9.0-wfs-binaries
#
# The WFS sources in that fork (tsk/fs/wfsfs.c, wfsfs_dent.c, tsk_wfsfs.h) are
# under the Common Public License 1.0.
#
# Installs to ~/wfs-tools/{bin,lib} (override with WFS_HOME=...).

set -euo pipefail

WFS_HOME=${WFS_HOME:-$HOME/wfs-tools}
URL=https://github.com/gbatmobile/sleuthkit4.9.0-wfs/releases/download/v4.9.0-wfs-binaries/sleuthkit-4.9.0-wfs-bin.7z

for cmd in curl 7z; do
    command -v "$cmd" >/dev/null || { echo "missing dependency: $cmd (apt install p7zip-full curl)" >&2; exit 1; }
done

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

echo "Downloading $URL ..."
curl -fL "$URL" -o "$tmp/sleuthkit.7z"

echo "Extracting ..."
7z x -o"$tmp/out" "$tmp/sleuthkit.7z" >/dev/null

# Locate the bin/ and lib/ directories wherever the archive nests them.
src_bin=$(find "$tmp/out" -type d -name bin | head -1)
src_lib=$(find "$tmp/out" -type d -name lib | head -1)
[ -n "$src_bin" ] && [ -n "$src_lib" ] || { echo "unexpected archive layout" >&2; exit 1; }

mkdir -p "$WFS_HOME"
rm -rf "$WFS_HOME/bin" "$WFS_HOME/lib"
cp -a "$src_bin" "$WFS_HOME/bin"
cp -a "$src_lib" "$WFS_HOME/lib"

# Install the wrapper + helper scripts from this directory.
here=$(cd "$(dirname "$0")" && pwd)
for s in wfs wfs-extract wfs-play; do
    [ -f "$here/$s" ] && install -m 0755 "$here/$s" "$WFS_HOME/$s"
done

echo
echo "Installed to $WFS_HOME"
"$WFS_HOME/wfs" fsstat -V 2>/dev/null | head -1 || true
echo "Try: $WFS_HOME/wfs fsstat /dev/mmcblk0"
