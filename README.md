- [Orange pi 5 Media Box](#orange-pi-5-media-box)
  - [initial setup](#initial-setup)
    - [Delete partitions](#delete-partitions)
    - [Get image into Downloads to flash nvme](#get-image-into-downloads-to-flash-nvme)
    - [UPDATE AND RECONFIGURE AFTER MIGRATION](#update-and-reconfigure-after-migration)
    - [Benchmark](#benchmark)

# Orange pi 5 Media Box

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

### Get image into Downloads to flash nvme
```bash
cd /home/orangepi/Downloads
ls -lah
sudo dd bs=1M if=Orangepi5_1.1.6_ubuntu_jammy_server_linux5.10.110.img of=/dev/nvme0n1 status=progress
sudo shutdown -h now # REMOVE SDCARD THEN POWER UP WITH BUTTON
```

### UPDATE AND RECONFIGURE AFTER MIGRATION
```bash
sudo apt update && sudo apt upgrade -y
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