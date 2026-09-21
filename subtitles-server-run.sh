#!/usr/bin/env bash

pushd ~/src/milahu/opensubtitles-scraper

port=$(grep -m1 "^server.port = " docs/lighttpd.conf.live | awk '{print $3 }')

echo starting https://pontus.feralhosting.com/milahu/bin/get-subtitles

NIXPKGS_ALLOW_UNFREE=1 exec nix-shell ./shell.nix.server.nix --run ./lighttpd.sh
