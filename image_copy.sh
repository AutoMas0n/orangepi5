#!/bin/bash

export SSHPASS='orangepi'
sshpass -e ssh -t root@192.168.2.210 'mount -o remount,size=10G /tmp && echo $SSHPASS | rm -rf /tmp/* && rm -rf /home/orangepi/Downloads/*' && sshpass -e rsync --progress -e 'ssh -o StrictHostKeyChecking=no' /home/jesse/Downloads/custom_ubuntu/ubuntu-22.04.3-custom-arm64-orangepi-5.img root@192.168.2.210:/tmp/ && sshpass -e ssh -t root@192.168.2.210 'echo $SSHPASS | sudo -S mv /tmp/ubuntu-22.04.3-custom-arm64-orangepi-5.img /home/orangepi/Downloads/ubuntu-22.04.3-preinstalled-desktop-arm64-orangepi-5.img'