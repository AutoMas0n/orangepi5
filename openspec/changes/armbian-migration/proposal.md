## Why

The Orange Pi 5 currently runs Ubuntu 22.04 (jammy), which has reached its stable end-of-life and relies on an outdated kernel (5.10-rockchip). Armbian provides a more actively maintained rockchip kernel, better hardware support (GPU drivers, thermal management, kernel updates), and a longer support lifecycle — all critical for a 24/7 home media server. This migration moves the existing services onto Armbian with zero behavior change to the media stack itself.

## What Changes

- **OS**: Ubuntu 22.04 LTS → Armbian (Debian-based, rockchip-optimized kernel)
- **Provisioning**: Replace the existing Ansible-based post-boot setup with a reliable, documented, step-by-step recovery procedure that is resilient to system quirks (Ansible was flaky for full reprovision)
- **No behavioral changes**: All Docker services, storage layout, network config, and user workflows remain identical

## Capabilities

This change describes no new or modified system capabilities — the platform is replaced while preserving every existing behavior. The specs describe what the system does; since nothing in that contract changes, no spec file is needed.

(The change's `.openspec.yaml` will set `skip_specs: true`.)

## Impact

| Area | Impact |
|---|---|
| **OS** | Ubuntu 22.04 → Armbian. Fresh install from Armbian image. Kernel upgrades from rockchip-optimized repos. |
| **Storage layout** | Unchanged. NVMe partition scheme and BTRFS RAID1 mount points remain the same. |
| **Docker stack** | All containers stop during migration. Configs (bind mounts in `~/Documents/`) are restored from backup. Images are re-pulled fresh. |
| **Data** | `/home` backed up to separate drive. `/media` moved temporarily (torrents). Both restored post-flash. |
| **Network** | Same static IP assignment, same service ports. |
| **Provisioning** | Step-by-step documented recovery procedure (replaces unreliable Ansible). |