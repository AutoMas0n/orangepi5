## Creating a Fully Customizable qBittorrent Docker Container with Configuration as Code

Yes, you can create a fully customizable qBittorrent Docker container with configuration as code by using Docker volumes to provide configuration files and by setting environment variables. Here's an example of how you can do this using a `docker-compose.yml` file:

```yaml
version: '3'
services:
  qbittorrent:
    image: linuxserver/qbittorrent
    container_name: qbittorrent
    environment:
      - PUID=1000 # Replace with your user id
      - PGID=1000 # Replace with your group id
      - TZ=Europe/London # Replace with your timezone
      - UMASK_SET=022 # Optional: Set permissions for newly created files
      - WEBUI_PORT=8080 # Optional: Set the port for the web interface
      - WebUI_Password_PBKDF2="@ByteArray(ARQ77eY1NUZaQsuDHbIMCA==:0WMRkYTUWVT9wVvdDtHAjU9b3b7uB8NR1Gur2hmQCvCDpm39Q+PsJRJPaCU51dEiz+dTzh8qbPsL8WkFljQYFQ==)"
    volumes:
      - /path/to/config:/config # Replace with the path to your qBittorrent config files
      - /path/to/downloads:/downloads # Replace with the path to your download folder
    ports:
      - "6881:6881"
      - "6881:6881/udp"
      - "8080:8080" # Match WEBUI_PORT if changed
    restart: unless-stopped
```

In the above `docker-compose.yml` file, replace `/path/to/config` with the path to the directory on your host system where you want to store qBittorrent's configuration files. This directory will contain the `qBittorrent.conf` file, which you can edit to change qBittorrent's settings without using the UI.

For example, you can configure the `qBittorrent.conf` file with your desired settings, like so:

```ini
[Preferences]
Downloads\SavePath=/downloads/
Connection\PortRangeMin=6881
WebUI\Port=8080
WebUI\Password_PBKDF2="@ByteArray(ARQ77eY1NUZaQsuDHbIMCA==:0WMRkYTUWVT9wVvdDtHAjU9b3b7uB8NR1Gur2hmQCvCDpm39Q+PsJRJPaCU51dEiz+dTzh8qbPsL8WkFljQYFQ==)"
```

Make sure to create the configuration directory and the `qBittorrent.conf` file on your host system before starting the Docker container. When you start the container, qBittorrent will use the provided configuration file.

To deploy this container, save the `docker-compose.yml` file and run:

```bash
sudo docker-compose up -d
```

You can also set additional qBittorrent settings through environment variables provided by the Docker image you are using. Check the documentation for the specific qBittorrent Docker image you choose for any additional environment variables that can be set for further customization.

## Troubleshooting
```bash
sudo docker-compose down --volumes
```

## TODO ANSIBLE
DOWNLOADS_PATH=/media  
- create path
- Give the above access permission

## TODO prereqs
- setup secrets
- figure out giving default password

## TODO Jackett
`http://localhost:9117/`
https://raw.githubusercontent.com/qbittorrent/search-plugins/master/nova3/engines/jackett.py

- setup jackett apikey
    - https://github.com/qbittorrent/search-plugins/wiki/How-to-configure-Jackett-plugin
```
Jackett: api key error! Right-click this row and select 'Open description page' to open help. Configuration file: '/config/qBittorrent/nova3/engines/jackett.json'
```
```json
{
    "api_key": "YOUR_API_KEY_HERE",
    "url": "http://127.0.0.1:9117",
    "tracker_first": false,
    "thread_count": 20
}
```

```bash
sudo docker exec -u root -it qbittorrent /bin/sh
```

```bash
sudo docker run --name qbittorrent2 --user root --entrypoint /bin/sh -it lscr.io/linuxserver/qbittorrent:latest
```