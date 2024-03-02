#!/bin/bash

# This script assumes you are on x86 making changes to aarch64 fs (qemu)
IMG_PATH="/home/jesse/Downloads/custom_ubuntu/ubuntu-22.04.3-custom-arm64-orangepi-5.img"
MOUNT_POINT="/mnt/ubuntu-img"

mkdir -p $MOUNT_POINT/{dev,proc,sys,boot}
losetup -P /dev/loop0 $IMG_PATH
mount /dev/loop0p2 $MOUNT_POINT
for dir in dev proc sys; do
    mount --bind /$dir $MOUNT_POINT/$dir
done

apt-get install qemu-user-static -y
cp /usr/bin/qemu-aarch64-static $MOUNT_POINT/usr/bin

chroot /mnt/ubuntu-img /usr/bin/qemu-aarch64-static /bin/bash <<EOF
touch /etc/sudoers.d/orangepi
echo "orangepi ALL=(ALL:ALL) ALL" | tee /etc/sudoers.d/orangepi
useradd -p $(openssl passwd -1 orangepi) orangepi
chmod 0440 /etc/sudoers.d/orangepi
echo orangepi:orangepi | chpasswd
chown orangepi:orangepi /home/orangepi
sudo chmod 750 /home/orangepi

systemctl disable oem-config.service
systemctl disable oem-config.target

# Check for additional services that may need to be disabled
systemctl list-unit-files | grep oem-config

#Remove startup wizard
rm -rf /var/lib/oem-config
apt-get remove -y oem-config-gtk ubiquity-frontend-gtk ubiquity-slideshow-ubuntu

#Remove startup popup for gnome-initial-setup
mkdir -p /etc/skel/.config
printf yes | tee /etc/skel/.config/gnome-initial-setup-done >/dev/null


EOF
./unmount.sh