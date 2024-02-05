sudo  apt-get install python3-launchpadlib -y \
  &&  sudo add-apt-repository ppa:liujianfeng1994 / panfork-mesa -y \
  &&  sudo add-apt-repository ppa:liujianfeng1994 / rockchip-multimedia -y

sudo apt-get update -y && \
sudo apt-get dist-upgrade -y && \
echo "deb [trusted=yes] http://ppa.launchpad.net/liujianfeng1994/panfork-mesa/ubuntu jammy main" | sudo tee /etc/apt/sources.list.d/liujianfeng1994-ubuntu-panfork-mesa-jammy.list && \
echo "deb [trusted=yes] http://ppa.launchpad.net/liujianfeng1994/rockchip-multimedia/ubuntu jammy main" | sudo tee /etc/apt/sources.list.d/liujianfeng1994-ubuntu-rockchip-multimedia-jammy.list && \
sudo apt-get update -y && \
sudo apt-get install mali-g610-firmware rockchip-multimedia-config -y

sudo  apt-get install gstreamer1.0-rockchip gstreamer1.0-plugins-base-apps gstreamer1.0-plugins-bad gstreamer1.0-plugins-good -y

sudo  apt-get install libd3dadapter9-mesa libegl-mesa0 libegl1-mesa libgbm1 libgl1-mesa-dri libgl1-mesa-glx libglapi-mesa libgles2-mesa libglx-mesa0 libosmesa6 libwayland-egl1-mesa mesa-common-dev mesa-va-drivers mesa-vdpau-drivers mesa-vulkan-drivers -y &&  sudo reboot now # https://t.me/Orange_Pi_Devices/157071


### SCRIPT

```bash
#!/bin/bash
for device in /dev/mtdblock0 /dev/nvme0n1; do
  # List partitions and extract the partition numbers
  part_numbers=$(sudo gdisk "$device" << EOF | awk '/^[[:blank:]]*[0-9]+[[:blank:]]+/{print $1}'
p
q
EOF
  )
  
  if [ -n "$part_numbers" ]; then
    # Generate the delete commands for gdisk
    gdisk_cmds="p" # Initialize with print command
    for part_num in $part_numbers; do
      gdisk_cmds="$gdisk_cmds\nd\n$part_num" # Append delete commands
    done
    gdisk_cmds="$gdisk_cmds\nw\nY" # Append write and confirm commands
    
    # Execute the delete commands in gdisk
    echo -e "$gdisk_cmds" | sudo gdisk "$device"
  else
    echo "No partitions found on $device."
  fi
done
```