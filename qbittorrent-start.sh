#!/usr/bin/env bash

set -x

export LANG="C.UTF-8"

while true; do

  qbittorrent-nox

  ~/scripts/screen-dump.sh qb
  mkdir -p log
  mv "$(ls -t screen.qb.*.txt | head -n1)" log/
  # wait before restart
  sleep 5m

done
