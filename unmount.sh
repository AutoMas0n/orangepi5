#!/bin/bash

# Function to unmount a mount point
unmount_point() {
    if mountpoint -q "$1"; then
        echo "Unmounting $1"
        sudo umount "$1"
    fi
}

# Unmount all bind mounts within the chroot environment
unmount_point /mnt/ubuntu-img/dev/pts
unmount_point /mnt/ubuntu-img/dev
unmount_point /mnt/ubuntu-img/proc
unmount_point /mnt/ubuntu-img/sys

# Unmount the primary mount point
unmount_point /mnt/ubuntu-img

# Detach all associated loop devices
for loop_device in $(losetup -l | awk '{if(NR>1)print $1}'); do
    # Find all mounts associated with this loop device and unmount them
    for assoc_mount in $(findmnt -nlo TARGET -S "$loop_device"); do
        unmount_point "$assoc_mount"
    done

    # Detach the loop device
    echo "Detaching $loop_device"
    sudo losetup -d "$loop_device"
done

echo "All loop devices have been detached and mount points unmounted."