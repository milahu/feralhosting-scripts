#!/usr/bin/env python3

# FIXME add_peers requires qbittorrent 4.4 ... i have 4.3.9

# https://github.com/milahu/cas_torrent/raw/main/scripts/qbittorrent-move-to-cas.py

# move all finished torrents to ~/cas/btih/{btih}

# https://github.com/rmartin16/qbittorrent-api
# https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)
# https://qbittorrent-api.readthedocs.io/en/latest/
# https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)#set-torrent-location
# https://qbittorrent-api.readthedocs.io/en/latest/apidoc/torrents.html#qbittorrentapi.torrents.TorrentDictionary.set_location
# https://github.com/rmartin16/qbittorrent-api/raw/main/src/qbittorrentapi/torrents.py

import os
import re
import sys
import time
import qbittorrentapi



# config
conn_info = dict(
    # $ grep proxy_pass ~/.nginx/conf.d/000-default-server.d/wiki-qbittorrent.conf
    # proxy_pass http://10.0.10.19:9001/;
    host="10.0.10.19",
    # $ grep '^WebUI\\Port' .config/qBittorrent/qBittorrent.conf
    # WebUI\Port=9001
    port=9001,
    username="milahu",
    password="6ZFnOBcHbdZmqER",
)


peer = sys.argv[1]

if not re.fullmatch(r"[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}:[0-9]{1,5}", peer):
    print("error: peer must be ipaddr:port for example 101.102.103.104:6881")
    sys.exit(1)

with qbittorrentapi.Client(**conn_info) as qbt_client:

    # display qBittorrent info
    if False:
        print(f"qBittorrent: {qbt_client.app.version}")
        print(f"qBittorrent Web API: {qbt_client.app.web_api_version}")
        for k, v in qbt_client.app.build_info.items():
            print(f"{k}: {v}")

    for torrent in qbt_client.torrents_info():

        #print(f"torrent {torrent.hash} {torrent.name} {torrent.state} {torrent.content_path}")

        # TODO remove? move all torrents
        if not torrent.state in finished_states:
            continue

        # usually, save_path is the parent directory of content_path
        src = torrent.save_path
        src2 = torrent.content_path

        if src.startswith(dst_dir + "/"):
            continue

        if not src.startswith(src_dir):
            print("unexpected src", src)
            print("src_dir", src_dir)
            continue

        print(f"torrent {torrent.hash} {torrent.name} {torrent.state} {torrent.content_path}")

        btih = torrent.info.hash
        dst = dst_dir + "/btih/" + btih.lower()
        dst2 = dst_dir + "/btih/" + btih.lower() + src2[len(src_dir):]

        wait_for_check = False

        if os.path.exists(dst):
            print("note: dst exists. qbittorrent will check files.", dst)
            wait_for_check = True

        os.makedirs(os.path.dirname(dst), exist_ok=True)

        # move torrent files
        # https://github.com/rmartin16/qbittorrent-api/raw/main/src/qbittorrentapi/torrents.py
        # def set_location
        print("src", src)
        print("src2", src2)
        print("dst", dst)
        print("dst2", dst2)
        #print("dst_parent", dst_parent)
        #torrent.set_location(dst_parent)
        torrent.set_location(dst)

        checking_states = (
            "checkingUP", # Torrent has finished downloading and is being checked
            "checkingDL", # Same as checkingUP, but torrent has NOT finished downloading
            "checkingResumeData", # Checking resume data on qBt startup
        )

        # only one moving state:
        # moving  Torrent is moving to another location

        def get_state():
            # TODO better. get state of one torrent
            for torrent2 in qbt_client.torrents_info():
                if torrent2.info.hash != torrent.info.hash:
                    continue
                return torrent2.state

        # TODO refactor checking and moving

        if get_state() in checking_states:
            print("waiting: qbittorrent is checking files ", end="")
            sys.stdout.flush()
            time.sleep(2)
            # todo timeout
            while get_state() in checking_states:
                print(".", end="")
                sys.stdout.flush()
                time.sleep(2)
            print(" ok")

        if get_state() == "moving":
            print("waiting: qbittorrent is moving files ", end="")
            sys.stdout.flush()
            time.sleep(2)
            # todo timeout
            while get_state() == "moving":
                print(".", end="")
                sys.stdout.flush()
                time.sleep(2)
            print(" ok")



print(f"TODO make sure all torrents are finished, then ...")
print(f"TODO rm -rf {src_dir}/*")
