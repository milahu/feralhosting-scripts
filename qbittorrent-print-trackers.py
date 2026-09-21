#!/usr/bin/env python3

# debug: print trackers

# https://github.com/arvidn/libtorrent/issues/7535#issuecomment-4149921519

import os
import json
import qbittorrentapi

# example config:
"""
{
  "host": "127.0.0.1",
  "port": 9001,
  "username": "admin",
  "password": "xxx"
}
"""
qbt_config_path = os.path.expanduser("~/.config/qbittorrentapi.json")
with open(qbt_config_path) as f:
    conn_info = json.load(f)

qbt_client = qbittorrentapi.Client(**conn_info)

tracker_urls = dict()
# https://qbittorrent-api.readthedocs.io/en/latest/apidoc/torrents.html#qbittorrentapi.torrents.TorrentsAPIMixIn.torrents_info
for torrent in qbt_client.torrents_info(status_filter="seeding"):
  for tracker in torrent.trackers:
    if tracker.tier == -1: continue # dht pex lsd
    if tracker.url in tracker_urls:
      tracker_urls[tracker.url] += 1
    else:
      tracker_urls[tracker.url] = 1
tracker_urls = list(tracker_urls.items())
# sort by count descending
tracker_urls.sort(key=lambda x: -1*x[1])
for url, count in tracker_urls:
  print(count, url)
