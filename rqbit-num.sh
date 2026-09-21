#!/bin/sh

curl -s http://127.0.0.1:3034/torrents |
jq '.torrents[] | .id' | wc -l
