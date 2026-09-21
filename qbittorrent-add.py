#!/usr/bin/env python3

# move all finished torrents
# from rqbit to qbittorrent

# FIXME also copy the priority of files
# example: NSL Archiv
# -> only download: Musik, Hörbücher

# https://github.com/rmartin16/qbittorrent-api
# https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)
# https://qbittorrent-api.readthedocs.io/en/latest/
# https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)#set-torrent-location
# https://qbittorrent-api.readthedocs.io/en/latest/apidoc/torrents.html#qbittorrentapi.torrents.TorrentDictionary.set_location
# https://github.com/rmartin16/qbittorrent-api/raw/main/src/qbittorrentapi/torrents.py

import os
import sys
import time
import dataclasses
import json

import qbittorrentapi
import torf


# config

cas_config_path = os.path.expanduser("~/.config/cas.json")
# example config:
"""
{
  "dirs": [
    "/run/media/user/WSC14YZM_8TB/cas"
  ]
}
"""

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


with open(cas_config_path) as f:
    cas_config = json.load(f)
cas_path_list = cas_config["dirs"]

with open(qbt_config_path) as f:
    conn_info = json.load(f)


def main():
    with qbittorrentapi.Client(**conn_info) as qbt_client:
        return main_inner(qbt_client)


def main_inner(qbt_client):

    #if qbt_client.torrents_add(urls="...") != "Ok.":
    #    raise Exception("Failed to add torrent.")

    # display qBittorrent info
    if 1:
        print(f"qBittorrent: {qbt_client.app.version}")
        print(f"qBittorrent Web API: {qbt_client.app.web_api_version}")
        for k, v in qbt_client.app.build_info.items():
            print(f"{k}: {v}")

    for torrent_file_path in sys.argv[1:]:

        print("-"*40)

        print("torrent_file_path", torrent_file_path)
        assert os.path.exists(torrent_file_path)

        try:
            torrent = torf.Torrent.read(torrent_file_path)
        except Exception as exc:
            print(f"ignoring invalid torrent file: {exc}")
            continue

        btih = torrent.infohash
        print("torrent", torrent.infohash, torrent.name)

        #content_path = torrent.directory_base
        #print("content_path", content_path)

        #content_dir_path = os.path.dirname(content_path)
        content_dir_path = None
        for cas_path in cas_path_list:
            content_dir_path = os.path.join(cas_path, "btih", torrent.infohash)
            if os.path.exists(content_dir_path):
                break
            else:
                content_dir_path = None
        if not content_dir_path:
            print("error: no content files")
            continue
        print("content_dir_path", content_dir_path)

        # check if qbittorrent already has this torrent
        # todo check if a torrent file is loaded
        # add torrent again
        # if qbittorrent is fetching metadata
        has_torrent = False
        for torrent2 in qbt_client.torrents_info():
            if 1:
                try:
                    btih2 = torrent2.info.hash
                except AttributeError:
                    # 'TorrentDictionary' instance has no attribute 'hash'
                    continue
            # btih2 = torrent2.info.hash
            if btih.lower() == btih2.lower():
                has_torrent = True
                break

        if has_torrent:
            print("already in qbittorrent")
            continue

        print("adding to qbittorrent", btih)
        try:
            qbt_client.torrents.add(
                # urls = btih,
                torrent_files = torrent_file_path,
                save_path = content_dir_path,
                # is_paused = True,
                is_sequential_download = True, # should be default...
                #tags = ["rqbit"],
                #forced = True,
            )
        #except qbittorrentapi.exceptions.UnsupportedMediaType415Error as exc:
        except Exception as exc:
            print("FIXME failed to add torrent to qbittorrent", btih, exc)
            continue

        continue

        print("waiting: qbittorrent is adding torrent ", end="")
        sys.stdout.flush()
        done_start = False
        # while not done_start:
        for _ in range(12):
            if done_start:
                break
            print(".", end="")
            sys.stdout.flush()
            time.sleep(5)
            for torrent2 in qbt_client.torrents.info():
                try:
                    btih2 = torrent2.info.hash
                except AttributeError:
                    # 'TorrentDictionary' instance has no attribute 'hash'
                    continue
                if btih.lower() == btih2.lower():
                    # torrent2.pause()
                    torrent2.resume()
                    done_start = True
                    break
        print(" ok")



        # wait for checking

        def get_state():
            # TODO better. get state of one torrent
            for torrent2 in qbt_client.torrents_info():
                # AttributeError: 'Torrent' object has no attribute 'info'
                if torrent2.info.hash.lower() != btih.lower():
                    continue
                return torrent2.state

        checking_states = (
            "checkingUP", # Torrent has finished downloading and is being checked
            "checkingDL", # Same as checkingUP, but torrent has NOT finished downloading
            "checkingResumeData", # Checking resume data on qBt startup
        )

        #if get_state() in checking_states:
        print("waiting: qbittorrent is checking files ", end="")
        sys.stdout.flush()
        time.sleep(2)
        # todo timeout
        # while get_state() in checking_states:
        for _ in range(12):
            if not get_state() in checking_states:
                break
            print(".", end="")
            sys.stdout.flush()
            time.sleep(5)
        print(" ok")



        # break # debug



if __name__ == "__main__":

    main()
