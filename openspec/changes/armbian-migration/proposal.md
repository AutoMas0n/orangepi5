## Why

The Orange Pi 5 currently runs Ubuntu 22.04 (jammy), which has reached its stable end-of-life and relies on an outdated kernel (5.10-rockchip). Armbian provides a more actively maintained rockchip kernel, better hardware support (GPU drivers, thermal management, kernel updates), and a longer support lifecycle — all critical for a 24/7 home media server. This was planned as a zero-behaviour-change migration. **It was not one.** The OS migration succeeded and the media survived, but the stack's *service state* — qBittorrent's torrents and resume data, Jackett's indexers, Jellyfin's library — was not inside the backup set and was lost with the old filesystem. Design decision 10 is the full account; the fix is a machine-checked backup-coverage rule rather than an assumption about where configs live.

## What Changes

- **OS**: Ubuntu 22.04 LTS → Armbian (Debian-based, rockchip-optimized kernel)
- **Provisioning**: Replace the existing Ansible-based post-boot setup with a reliable, documented, step-by-step recovery procedure that is resilient to system quirks (Ansible was flaky for full reprovision)
- **⚠️ Service state lost, and not restored**: qBittorrent's torrent list / `.fastresume` data / categories, Jackett's indexer definitions, and Jellyfin's library were in `/root/Documents` (Compose expanded `~` against `$HOME`, and the stack script runs as root) — outside the backed-up `/home` + `/media`. Unrecoverable: the migration then overwrote the region of the disk that held them. Recovered from git by luck: the Jackett API key. See design decisions 10 and 13
- **Jellyfin retired**: it lost the most state and was the only service needing hardware-specific patching (`/dev/dri/renderD129` no longer exists). Deliberately removed rather than rebuilt (decision 12)
- **VPN config generation replaced**: `pia-wg-config` targets an endpoint that now returns 404; WireGuard configs are minted by `docker/refresh-wireguard.sh`, wrapping PIA's maintained tooling (decision 9)
- **Resilience added**: gluetun had no restart policy (one reboot from taking the stack offline); now ordered boot start plus a self-healing watchdog that eventually rotates the VPN server (decision 11)
- **Tidied**: dead Go tooling, stale duplicate directories and the inert `qBittorrent-data.conf` mount removed; state paths made absolute and coverage made checkable (decisions 10, 13)

## Capabilities

This change describes no new or modified system capabilities — the platform is replaced while preserving every existing behavior. The specs describe what the system does; since nothing in that contract changes, no spec file is needed.

(The change's `.openspec.yaml` will set `skip_specs: true`.)

## Impact

| Area | Impact |
|---|---|
| **OS** | Ubuntu 22.04 → Armbian. Fresh install from Armbian image. Kernel upgrades from rockchip-optimized repos. |
| **Storage layout** | Unchanged. NVMe partition scheme and BTRFS RAID1 mount points remain the same. |
| **Docker stack** | All containers stop during migration. Images are re-pulled fresh (5 — Jellyfin retired). **Configs were NOT restored: the live state was never in the backup** (decision 10). The stack's config must be rebuilt: torrents re-added (payloads intact in `/media`), Jackett indexers re-added (API key preserved), qBittorrent WebUI password set. |
| **App state** | **Lost and unrecoverable** — qBittorrent torrents/resume data, Jackett indexers/credentials, Jellyfin library and watch history. |
| **Data** | `/home` and `/media` (133 G, 289 files) backed up to a separate drive and restored verified. Nothing else was in the backup set. |
| **Network** | Same static IP (192.168.2.113) and ports; interface is `end0` under Armbian and the NIC's MAC differs from the baseline. |
| **VPN** | WireGuard retained for performance (389 Mbps measured); config generation moved to PIA's current flow; self-healing watchdog added. |
| **Provisioning** | Step-by-step documented recovery procedure (replaces unreliable Ansible). |