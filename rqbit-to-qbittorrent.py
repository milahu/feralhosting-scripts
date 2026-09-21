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

import requests
import qbittorrentapi


# config
rqbit_base = "http://127.0.0.1:3034/"
rqbit_cache_path = os.path.expanduser("~/.cache/rqbit")
cas_path = os.path.expanduser("~/cas")
conn_info = dict(
    # $ grep proxy_pass ~/.nginx/conf.d/000-default-server.d/wiki-qbittorrent.conf
    # proxy_pass http://10.0.10.19:9001/;
    #host="10.0.10.19",
    #host="127.0.0.1",
    host="10.0.18.33", # ipaddr.sh
    # $ grep '^WebUI\\Port' .config/qBittorrent/qBittorrent.conf
    # WebUI\Port=9001
    port=9001,
    username="admin",
    password="qbitqbit8876qbit",
)


###################


import json
from types import SimpleNamespace


# Parse JSON into an object with attributes corresponding to dict keys.
def json_loads(s):
    f = lambda d: SimpleNamespace(**d)
    return json.loads(s, object_hook=f)


def rqbit_remove(btih):
    path = f"torrents/{btih}/forget"
    res = requests.post(rqbit_base + path)
    res.raise_for_status()
    #res = json_loads(res.text)
    print(res.text)


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

    res = requests.get(rqbit_base + "torrents")
    res.raise_for_status()
    res = json_loads(res.text)

    for torrent in res.torrents:

        btih = torrent.info_hash

        print("torrent", torrent.info_hash, torrent.name)

        torrent_file_path = os.path.join(rqbit_cache_path, torrent.info_hash + ".torrent")
        print("torrent_file_path", torrent_file_path)
        assert os.path.exists(torrent_file_path)

        #content_path = torrent.directory_base
        #print("content_path", content_path)

        #content_dir_path = os.path.dirname(content_path)
        content_dir_path = os.path.join(cas_path, "btih", torrent.info_hash)
        print("content_dir_path", content_dir_path)
        assert os.path.exists(content_dir_path)

        # check if qbittorrent already has this torrent
        has_torrent = False
        for torrent2 in qbt_client.torrents_info():
            btih2 = torrent2.info.hash
            if btih.lower() == btih2.lower():
                has_torrent = True
                break

        if has_torrent:
            print("already in qbittorrent")
            print("removing from rqbit")
            rqbit_remove(btih)
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
                # force start to avoid "stalledUP" state
                forced = True,
            )
        #except qbittorrentapi.exceptions.UnsupportedMediaType415Error as exc:
        except Exception as exc:
            print("FIXME failed to add torrent to qbittorrent", btih, exc)

        # does "close" delete the torrent from the download list?
        # but it should keep the downloaded files = content
        print("removing from rqbit")
        rqbit_remove(btih)

        # dont wait for "checking files"
        continue

        print("waiting: qbittorrent is adding torrent ", end="")
        sys.stdout.flush()
        done_start = False
        while not done_start:
            print(".", end="")
            sys.stdout.flush()
            time.sleep(5)
            for torrent2 in qbt_client.torrents.info():
                btih2 = torrent2.info.hash
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
                try:
                    if torrent2.info.hash.lower() != btih.lower():
                        continue
                except AttributeError:
                    # AttributeError: 'TorrentDictionary' instance has no attribute 'hash'
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
        while get_state() in checking_states:
            print(".", end="")
            sys.stdout.flush()
            time.sleep(2)
        print(" ok")



        print("-"*40)



        #break # debug



if __name__ == "__main__":

    main()
