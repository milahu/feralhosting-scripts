#!/bin/sh
exec nix-shell -p qbittorrent-nox --run "qbittorrent-nox --profile=$HOME/.config/qbittorrent-nox-2 --webui-port=9015 --save-path=$HOME/qbittorrent-nox-2 --sequential"
