- [Orange pi 5 Media Box](#orange-pi-5-media-box)
  - [initial setup](#initial-setup)
    - [Delete partitions](#delete-partitions)
      - [SHORTCUT](#shortcut)
    - [Get image into Downloads to flash nvme](#get-image-into-downloads-to-flash-nvme)
    - [Benchmark](#benchmark)
  - [Base Software Installation](#base-software-installation)
    - [FIREFOX](#firefox)
    - [Docker](#docker)
    - [docker jellyfin rockchip](#docker-jellyfin-rockchip)
    - [martin](#martin)
    - [THANK GOD SOMEONE DID THIS](#thank-god-someone-did-this)
- [HOST Apps](#host-apps)
  - [vs code](#vs-code)
  - [Firefox](#firefox-1)
- [TODO](#todo)
  - [Reference diagram](#reference-diagram)

# Orange pi 5 Media Box
https://www.crosstalksolutions.com/orange-pi-5-simple-overview-and-installation-with-m-2-ssd/
## initial setup
```bash
ifconfig
sudo apt update && sudo apt upgrade -y
fdisk -l
sudo gdisk /dev/mtdblock0 #Hit `p`
```
### Delete partitions
- `sudo gdisk /dev/mtdblock0`
```bash
Number  Start (sector)    End (sector)  Size       Code  Name
   1              64            7167   3.5 MiB     8300  idbloader
   2            7168            7679   256.0 KiB   8300  vnvm
   3            7680            8063   192.0 KiB   8300  reserved_space
   4            8064            8127   32.0 KiB    8300  reserved1
   5            8128            8191   32.0 KiB    8300  uboot_env
   6            8192           16383   4.0 MiB     8300  reserved2
   7           16384           32734   8.0 MiB     8300  uboot

Command (? for help): d
Partition number (1-7): 1

Command (? for help): d
Partition number (2-7): 2

Command (? for help): d
Partition number (3-7): 3

Command (? for help): d
Partition number (4-7): 4

Command (? for help): d
Partition number (5-7): 5

Command (? for help): d
Partition number (6-7): 6

Command (? for help): d
Using 7

Command (? for help): d
No partitions

Command (? for help): w

Final checks complete. About to write GPT data. THIS WILL OVERWRITE EXISTING
PARTITIONS!!

Do you want to proceed? (Y/N): Y
OK; writing new GUID partition table (GPT) to /dev/mtdblock0.
Warning: The kernel is still using the old partition table.
The new table will be used at the next reboot or after you
run partprobe(8) or kpartx(8)
The operation has completed successfully
```
- Do the same for `sudo gdisk /dev/nvme0n1`

#### SHORTCUT
```bash
# for 7
echo -e "p\nd\n1\nd\n2\nd\n3\nd\n4\nd\n5\nd\n6\nd\n7\nw\nY" | sudo gdisk /dev/mtdblock0 && echo -e "p\nd\n1\nd\n2\nd\n3\nd\n4\nd\n5\nd\n6\nd\n7\nw\nY" | sudo gdisk /dev/nvme0n1
# for 2
echo -e "p\nd\n1\nd\n2\nd\nd\nw\nY\nY" | sudo gdisk /dev/mtdblock0 && echo -e "p\nd\n1\nd\n2\nd\nd\nw\nY\nY" | sudo gdisk /dev/nvme0n1
```

### Get image into Downloads to flash nvme
```bash
cd /home/orangepi/Downloads && ls -lah && sudo dd bs=1M if=ubuntu-22.04.3-preinstalled-desktop-arm64-orangepi-5.img of=/dev/nvme0n1 status=progress && orangepi-config #apply option 7 for installs!
sudo shutdown -h now # REMOVE SDCARD THEN POWER UP WITH BUTTON
```

### Benchmark
sudo curl https://raw.githubusercontent.com/TheRemote/PiBenchmarks/master/Storage.sh | sudo bash

```
     Category                  Test                      Result
HDParm                    Disk Read                 369.24 MB/s
HDParm                    Cached Disk Read          371.00 MB/s
DD                        Disk Write                261 MB/s
FIO                       4k random read            53753 IOPS (215013 KB/s)
FIO                       4k random write           28603 IOPS (114413 KB/s)
IOZone                    4k read                   64651 KB/s
IOZone                    4k write                  98197 KB/s
IOZone                    4k random read            45374 KB/s
IOZone                    4k random write           75672 KB/s

                          Score: 18693

Compare with previous benchmark results at:
https://pibenchmarks.com/
```

## Base Software Installation
CHECK IF DOCKER IS ALREADY INSTALLED BEFORE DOING THIS!!
### FIREFOX
```bash
sudo apt install openbox xorg firefox -y
mkdir -p ~/.config/openbox
echo "firefox" > ~/.config/openbox/autostart
chmod +x ~/.config/openbox/autostart
```
`startx /usr/bin/openbox-session`
### Docker
To install Docker on Ubuntu Server and address the GPG key updates, follow these steps:

1. Update your existing list of packages:
```
sudo apt update
```

2. Install prerequisite packages which let `apt` use packages over HTTPS:
```
sudo apt install apt-transport-https ca-certificates curl software-properties-common
```

3. Download the GPG key for the Docker repository to your system:
```
cd ~
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o docker.gpg
```

4. Add the GPG key to your trusted keys:
```
sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg docker.gpg
```

5. Add the Docker repository to APT sources using the trusted keyring:
```
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```

6. Update the package database with the Docker packages from the newly added repo:
```
sudo apt update
```

7. Install Docker:
```
sudo apt install docker-ce docker-ce-cli containerd.io
```

8. Verify that Docker is installed and running:
```
sudo systemctl status docker
```

9. (Optional) To run Docker commands without `sudo`, add your user to the `docker` group:
```
sudo usermod -aG docker ${USER}
```

After adding your user to the `docker` group, you will need to log out and back in for this to take effect. Docker is now installed and ready for personal use on your Ubuntu Server.

### docker jellyfin rockchip
https://forum.armbian.com/topic/29742-jellyfin-docker-hardware-acceleration/
https://hub.docker.com/r/jjm2473/jellyfin-mpp

### martin
echo -e "\n" | ssh-keygen -t rsa -b 4096
cat ~/.ssh/id_rsa.pub

sudo apt install software-properties-common sudo add-apt-repository -y ppa:team-xbmc/kodi-old sudo apt update && sudo apt install kodi

If you want to install a specific version of Kodi, you need to modify the first task. Instead of `state: latest`, you would specify the version number with the `pkg` parameter like this:

```yaml
- name: Install Specific Version of Kodi
  apt:
    pkg: kodi=2:18.9+git20201024.0821-final-0bionic
    state: present
```

Replace `2:18.9+git20201024.0821-final-0bionic` with the actual version string you want to install.

### THANK GOD SOMEONE DID THIS
https://github.com/Joshua-Riek/ubuntu-rockchip

# HOST Apps
## vs code
Open your .bashrc file with the command `nano ~/.bashrc` in terminal. At the end of the file, add this line: `export PATH=$PATH:/home/jesse/groovy/groovy-4.0.15/bin` and `printf "\e[?2004l"`. Save and exit. Reload .bashrc with the command `source ~/.bashrc`. Now, you should be able to call groovy from anywhere.

https://groovy.apache.org/download.html
https://code.visualstudio.com/Download#
`sudo dpkg -i code_1.84.2-1699527205_arm64.deb`
```bash
git config --global user.name "Jesse"
git config --global user.email "jesse1819@gmail.com"
```

## Firefox
```
sudo add-apt-repository ppa:mozillateam/ppa
sudo apt install firefox-esr
```

# TODO
- Create own ansible script properly from ground up
  - Install docker
  - Install vs code
  - git setup scripts
  - Chromium configurations, extensions
    - master_preferences
      - https://askubuntu.com/questions/1241224/chromium-snap-new-profile-with-master-preferences#:~:text=One%20of%20those%20is%20the%20master_preferences%20file.&text=On%20Linux%2C%20this%20file%20is,data%2Ddir%3D~%2Fnew_profile%20).
      - https://www.chromium.org/developers/design-documents/first-run-customizations/#:~:text=Chromium%20can%20be%20customized%20to,as%20the%20chrome.exe%20binary.&text=There%20is%20one%20dictionary%2C%20called,list%2C%20called%20%22first_run_tabs%22.
    - Fix keyring on startup?
    - Enable memory saver by default
    - Look for firefox replacement
- Create and publish Docker images
  - Install PIA
    - PIA: docker pull qmcgaw/gluetun https://github.com/qdm12/gluetun
      - https://github.com/qdm12/gluetun-wiki/blob/main/setup/connect-a-container-to-gluetun.md
  - Install & Auto configure qbittorrent configs
    - https://docs.linuxserver.io/images/docker-qbittorrent/#docker-mods
  - BOTH??
    - https://hub.docker.com/r/binhex/arch-qbittorrentvpn/
  - Install Jellyfin
- Investigate secret management for docker images
  - HashiCorp Vault Free secrets
- Auto install watchtower, configure listener for image changes
- Create unit tests for container images and configs
- Investigate streaming and searching options
  - https://hub.docker.com/r/stremio/server/tags
  - https://web.stremio.com/#/detail/movie/tt11858890/tt11858890
  - https://torrentio.strem.fun/configure
  - https://blog.stremio.com/using-stremio-service/ OR https://torrentio.strem.fun/lite/configure
- Reinstall OS script using sd card

## Reference diagram
https://lemmy.ml/pictrs/image/ddc4c780-8776-4c4a-a344-1a571eeb8b12.webp