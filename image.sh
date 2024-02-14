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
apt-get install qemu-user-static -y
cp /usr/bin/qemu-aarch64-static /mnt/ubuntu-img/usr/bin
chroot /mnt/ubuntu-img /usr/bin/qemu-aarch64-static /bin/bash <<EOF
mkdir /isolinux
echo "
default live-install
label live-install
  menu label ^Install Ubuntu
  kernel /casper/vmlinuz.efi
  append  file=/cdrom/ks.preseed auto=true priority=critical debian-installer/locale=en_US keyboard-configuration/layoutcode=us ubiquity/reboot=true languagechooser/language-name=English countrychooser/shortlist=US localechooser/supported-locales=en_US.UTF-8 boot=casper automatic-ubiquity initrd=/casper/initrd.lz quiet splash noprompt noshell ---">/isolinux/txt.cfg

# KS.PRESEED may not be used anymore due to new ubuntu
echo "# # Partitioning removal of keys to prevent file sys error

ubiquity partman-auto/disk string /dev/sda
ubiquity partman-auto/method string regular
ubiquity partman-lvm/device_remove_lvm boolean true
ubiquity partman-md/device_remove_md boolean true
ubiquity partman-auto/choose_recipe select atomic

# automatically partition without confirmation
d-i partman-partitioning/confirm_write_new_label boolean true
d-i partman/choose_partition select finish
d-i partman/confirm boolean true
d-i partman/confirm_nooverwrite boolean true

# Locale
d-i debian-installer/locale string en_US
d-i console-setup/ask_detect boolean false
d-i console-setup/layoutcode string us

# Network
d-i netcfg/get_hostname string unassigned-hostname
d-i netcfg/get_domain string unassigned-domain
d-i netcfg/choose_interface select auto

# Clock
d-i clock-setup/utc-auto boolean true
d-i clock-setup/utc boolean true
d-i time/zone string US/Pacific
d-i clock-setup/ntp boolean true

# Packages, Mirrors, Image
d-i mirror/country string US
d-i apt-setup/multiverse boolean true
d-i apt-setup/restricted boolean true
d-i apt-setup/universe boolean true

# Users
d-i passwd/user-fullname string orangepi
d-i passwd/username string orangepi
d-i passwd/user-password-crypted password $6$pvgnJMUf7C44EBX8$632CGxSJE7Hj/cKMHhEM9FlvEflo2dr2SMrHNYcOHZ08vCiZn26exWo9eWumO0gd0VPjelwAD9aX9ruBGoz.F.
d-i passwd/user-default-groups string adm audio cdrom dip lpadmin sudo plugdev sambashare video
d-i passwd/root-login boolean true
d-i passwd/root-password-crypted password $6$pvgnJMUf7C44EBX8$632CGxSJE7Hj/cKMHhEM9FlvEflo2dr2SMrHNYcOHZ08vCiZn26exWo9eWumO0gd0VPjelwAD9aX9ruBGoz.F.
d-i user-setup/allow-password-weak boolean true
d-i pkgsel/include string openssh-server
d-i preseed/late_command string \
  in-target sh -c 'sed -i "s/^#PermitRootLogin.*\$/PermitRootLogin yes/g" /etc/ssh/sshd_config';
# Grub
# Due notably to potential USB sticks, the location of the MBR can not be
# determined safely in general, so this needs to be specified:

d-i grub-installer/bootdev  string /dev/sda

# To install to the first device (assuming it is not a USB stick):
#d-i grub-installer/bootdev  string default
d-i grub-installer/grub2_instead_of_grub_legacy boolean true
d-i grub-installer/only_debian boolean true
d-i finish-install/reboot_in_progress note

# Custom Commands (ssh access on install - change network device name as applicable)
ubiquity ubiquity/success_command \
    string echo "auto enp2s0" >> /etc/network/interfaces; \
           echo "iface enp2s0 inet dhcp" >> /etc/network/interfaces; \
           ifup enp2s0; \
           apt-get update -y; \
           in-target apt-get install -y openssh-server;">/ks.preseed

           
sudo mkdir -p /etc/skel/.config
printf yes | sudo tee /etc/skel/.config/gnome-initial-setup-done >/dev/null

# systemctl disable oem-config.service
# systemctl mask oem-config.service

# #### FIRSTBOOT
# echo "
# #! /bin/bash
# # Skipped oem-config on the first boot after shipping to the end user.
# set -e

# # Immediately proceed with automatic login setup, skipping configuration screens.
# # Assuming 'username' is the user you want to automatically log in.

# # if sddm.conf exists, add a comment to show that this is the original
# # version which existed before end user setup was run 
# if [ -f "/etc/sddm.conf" ]; then
#         echo "#original_oem_version" >> /etc/sddm.conf
# fi

# # Remove the oem-config-prepare menu item.
# rm -f /usr/share/applications/oem-config-prepare-gtk.desktop \
#       /usr/share/applications/kde4/oem-config-prepare-kde.desktop

# # Set up automatic login for the user.
# if [ -f "/etc/sddm.conf" ]; then
#         echo "[Autologin]" >> /etc/sddm.conf
#         echo "User=orangepi" >> /etc/sddm.conf
#         echo "Session=ubuntu.desktop" >> /etc/sddm.conf
# fi

# # Enable automatic login for the user.
# if [ -f "/etc/gdm3/custom.conf" ]; then
#         sed -i '/\[daemon\]/a AutomaticLoginEnable=True' /etc/gdm3/custom.conf
#         sed -i "/\[daemon\]/a AutomaticLogin=username" /etc/gdm3/custom.conf
# fi

# # Enable graphical.target as the default target to boot into GUI.
# /bin/systemctl set-default graphical.target || true
# /bin/systemctl disable oem-config.service || true
# /bin/systemctl disable oem-config.target || true
# rm -f /lib/systemd/system/oem-config.* || true

# # Ensure the system does not request to reboot.
# # /bin/systemctl reboot || true

# # Isolate graphical target without blocking.
# /bin/systemctl --no-block isolate graphical.target || true

# # Remove the script to prevent it from running again.
# rm -f /var/lib/oem-config/run

# exit 0 >/usr/sbin/oem-config-firstboot

EOF
./unmount.sh