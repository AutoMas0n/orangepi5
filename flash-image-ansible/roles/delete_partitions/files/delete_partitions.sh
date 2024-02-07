#!/bin/bash

devices=(/dev/mtdblock0 /dev/nvme0n1)

for device in "${devices[@]}"; do
  echo "Processing $device"

  # Get the list of partitions
  partition_list=$(sudo gdisk -l "$device" 2>/dev/null | awk '/^[[:space:]]*[0-9]+[[:space:]]+/{print $1}')

  # If partition_list is empty, no partitions to delete
  if [ -z "$partition_list" ]; then
    echo "No partitions to delete on $device"
    continue
  fi

  # Generate and execute the delete commands dynamically
  {
    echo "p" # Print the partition table first

    for partition in $partition_list; do
      echo "d" # Delete command
      echo "$partition" # Specify the partition number
    done

    echo "w" # Write changes
    echo "Y" # Confirm for gdisk
    echo "Y" # Additional confirmation if needed
  } | sudo gdisk "$device"
done