#!/bin/bash

# This script assumes you are on x86 making changes to aarch64 fs
mkdir /mnt/ubuntu-img
mkdir /mnt/ubuntu-img/dev
mkdir /mnt/ubuntu-img/proc
mkdir /mnt/ubuntu-img/sys
losetup -P /dev/loop0 /home/jesse/Downloads/custom_ubuntu/ubuntu-22.04.3-custom-arm64-orangepi-5.img
mount /dev/loop0p2 /mnt/ubuntu-img
mount --bind /dev /mnt/ubuntu-img/dev
mount --bind /proc /mnt/ubuntu-img/proc
mount --bind /sys /mnt/ubuntu-img/sys
apt-get install qemu-user-static
cp /usr/bin/qemu-aarch64-static /mnt/ubuntu-img/usr/bin
chroot /mnt/ubuntu-img /usr/bin/qemu-aarch64-static /bin/bash <<EOF
echo -e "orangepi\norangepi" | passwd orangepi
touch /etc/sudoers.d/orangepi
echo "orangepi ALL=(ALL:ALL) ALL" | tee /etc/sudoers.d/orangepi
chmod 0440 /etc/sudoers.d/orangepi
EOF
./unmount.sh