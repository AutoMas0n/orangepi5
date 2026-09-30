# Copyparty WebDAV Server

Copyparty is a portable file server with WebDAV support, allowing you to access your media files over the network.

## Setup

1. Create the config directory:
```bash
mkdir -p ~/Documents/copyparty
```

2. Start the container:
```bash
cd /home/jesse/GitHub/orangepi5/docker/copyparty
sudo docker-compose up -d
```

## Access

- **Web Interface**: http://localhost:3923
- **WebDAV URL**: http://localhost:3923/media/

## Configuration

The container is configured to:
- Mount `/media` as read-only with the following permissions:
  - `r` - read access
  - `c` - allow file listing
  - `e2d` - enable directory listing
  - `e2t` - enable thumbnails
- Run on port 3923
- Use PUID/PGID 30000 (matching your other containers)

## WebDAV Access

To mount the WebDAV share on various systems:

### Linux
```bash
# Install davfs2
sudo apt install davfs2

# Mount the share
sudo mount -t davfs http://localhost:3923/media/ /mnt/copyparty
```

### macOS
```bash
# In Finder, press Cmd+K and enter:
http://localhost:3923/media/
```

### Windows
```
Map Network Drive → http://localhost:3923/media/
```

## Notes

- This is running independently from Jellyfin, so you can test it without affecting your existing setup
- The media folder is mounted read-only for safety
- Config and metadata are stored in `~/Documents/copyparty`
- To stop: `sudo docker-compose down`
