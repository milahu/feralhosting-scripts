#!/usr/bin/env bash

# https://www.feralhosting.com/wiki/software/rclone

set -x

mkdir -p ~/bin
wget -qO ~/rclone.zip https://downloads.rclone.org/rclone-current-linux-amd64.zip
unzip ~/rclone.zip -d ~/
mv ~/rclone-v*-linux-amd64/rclone ~/bin
rm -rf ~/rclone-v*-linux-amd64 ~/rclone.zip
