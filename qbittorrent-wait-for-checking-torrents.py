#!/usr/bin/env python3

# wait for all checking torrents to finish checking

print("import...")
import os
import sys
import time
import re
import shutil
import urllib.parse
import dataclasses
import subprocess
import json
import shlex
import subprocess
import glob

print("import requests")
#import requests
print("import torf")
from torf import Torrent
import qbittorrentapi
import torf
import psutil



# config

# host is container ip address from ipaddr.sh
# example config:
"""
{
  "host": "10.0.18.33",
  "port": 9001,
  "username": "admin",
  "password": "xxx"
}
"""
qbt_config_path = os.path.expanduser("~/.config/qbittorrentapi.json")



###################



with open(qbt_config_path) as f:
    conn_info = json.load(f)

def main():
    with qbittorrentapi.Client(**conn_info) as qbt_client:
        return main_inner(qbt_client)


def main_inner(qbt_client):
    if 1:
        print(f"qBittorrent: {qbt_client.app.version}")
        print(f"qBittorrent Web API: {qbt_client.app.web_api_version}")
    last_hash = None
    while True:
        is_waiting = False
        for torrent in qbt_client.torrents_info("checking"):
            is_waiting = True
            # require progress > 0
            if torrent.progress == 0:
                continue
            if torrent.info.hash != last_hash:
                # print()
                print("checking torrent", torrent.info.hash, torrent.name)
            # else:
            #     print(".", end="")
            last_hash = torrent.info.hash
            break
        time.sleep(10)
        if not is_waiting:
            break
    # print()


if __name__ == "__main__":

    main()
