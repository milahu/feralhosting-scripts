#!/bin/sh
set -x
killall --wait rqbit
sleep 2
~/.config/feral/user-container.d/rqbit
