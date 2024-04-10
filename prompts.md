- [orangepi5](#orangepi5)
  - [The containers should all have access to a shared directory or volume to persist data.](#the-containers-should-all-have-access-to-a-shared-directory-or-volume-to-persist-data)

# orangepi5
I have an orange pi 5 8GB. I want to create a super easy to maintain media box that is used for downloading torrents and playing/streaming 4k content. 

I want to install an OS that has `apt` for installing packages and I don't want to have a UI at first, just a terminal. The OS should update itself regularly on it's own.

I want to install docker so that I can spin up containers when the OS starts up. 
I want to be able to check for latest container published on every boot and use the latest image, however appdata should stay intact when new images are fetched.
These are the containers I want to be able to configurably start on OS boot up:
- container that has a UI that I can optionally enable. This UI container will have VLC, a file browser and a browser installed, basically I want latest KDE Plasma for TV ecosystem.
- container that runs privateinternetaccess VPN, all programs inside of this container should only have internet access through the VPN, other containers should be able to connect without the VPN. This container should have qbittorrent installed and stremio. If the VPN is not working the killswitch should trigger and disable the internet connectivity in the container
- container that runs Jellyfin to access the media produced from the other container


The containers should all have access to a shared directory or volume to persist data.
---

To achieve your setup on the Orange Pi 5 8GB, follow these steps:

1. **Install a headless OS with `apt`:**
   Choose a headless version of a Debian-based distribution such as Ubuntu Server or Armbian. These systems use `apt` for package management and can be configured for unattended upgrades.

2. **Configure automatic updates:**
   Enable unattended-upgrades for automatic security updates. For Ubuntu, you can do this by installing the `unattended-upgrades` package and configuring `/etc/apt/apt.conf.d/50unattended-upgrades`.

3. **Install Docker:**
   Install Docker using the repository setup for your chosen distribution. Instructions can be found at the official Docker documentation.

4. **Automate Docker container updates:**
   Use a tool like `Watchtower` to automatically update your Docker containers to the latest image on boot while keeping app data intact. Configure Watchtower in your `docker-compose.yml` or Docker run command.

5. **Set up containers:**
   Create a `docker-compose.yml` file to configure your containers:

   - **UI Container:** Use a Docker image like `kdeneon/plasma:dev-unstable` for KDE Plasma. Set it to start with the system but without the UI initially.
   - **VPN Container:** Use an image like `qmcgaw/private-internet-access` or create a custom one with the VPN client, qbittorrent, and Stremio installed. Configure the network to use the VPN with a killswitch.
   - **Jellyfin Container:** Use the official Jellyfin image and configure it to start with the system.

6. **Shared directory/volume:**
   Define a Docker volume in your `docker-compose.yml` or use bind mounts to create a shared directory accessible by all containers for persistent data storage.

7. **Enable Docker and containers at boot:**
   Ensure Docker starts on boot with `systemctl enable docker`. Your `docker-compose.yml` will handle the automatic start-up of containers.

8. **Optional UI enablement:**
   Set up a way to start the KDE Plasma UI when needed, such as through a remote SSH command or by binding it to a specific runlevel or systemd target.

This setup requires customizing Docker images and writing a comprehensive `docker-compose.yml` file. Ensure you configure your network and volumes correctly for your VPN and media access requirements, and regularly back up your configuration and persistent data.

Remember, maintaining a system also includes regular manual checks and updates beyond automatic ones. Always test updates in a staging environment before deploying them to your live media box.

---

Yes, it is possible to preconfigure everything you need by creating custom Docker images and using Docker Compose to orchestrate container deployment. Here's how you can achieve this:

1. **Custom Docker Images:**
   - Create Dockerfiles for each of the custom containers you need.
   - In each Dockerfile, add the necessary configuration files, environment variables, and setup scripts.
   - Build the custom images and push them to a Docker registry (e.g., Docker Hub).

2. **Docker Compose:**
   - Write a `docker-compose.yml` file that specifies all the services (containers), their configurations, volumes, networks, and dependencies.
   - Use the `build` context in the Docker Compose file if you want to build images directly from your Dockerfiles.
   - Define environment variables in the Docker Compose file or an `.env` file that Docker Compose can use.

3. **Automation Scripts:**
   - Create scripts (e.g., shell scripts) that can run on the initial boot-up to set up Docker, Docker Compose, and any other system configurations.
   - These scripts can also pull the latest images and run `docker-compose up` to start all containers.

4. **Persistent Data:**
   - Configure volumes in your Docker Compose file to ensure app data persists across container updates.

5. **Auto-Update Configuration:**
   - Integrate an auto-update tool like Watchtower in your Docker Compose setup to automatically pull and use the latest container images.

6. **Remote Configuration Changes:**
   - If you need to make changes in the future, you can update your Dockerfiles or Docker Compose configurations remotely and redeploy your containers.

By preparing your Dockerfiles, Docker Compose file, and automation scripts ahead of time, you can minimize manual configuration after the initial setup. However, creating a completely hands-off system from the start can be complex and may still require some initial manual setup, especially for unique or custom configurations. It's also important to test your setup thoroughly to ensure everything works as expected before considering it maintenance-free.
