#!/bin/sh

# wiki/software/deluge.html

pkill -9 -fu "$(whoami)" 'deluged'
pkill -9 -fu "$(whoami)" 'deluge-web'
rm -rf ~/.config/deluge ~/private/deluge
