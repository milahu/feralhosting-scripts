#!/usr/bin/env python3

# remove torrents from rqbit

# https://github.com/ikatson/rqbit

import os
import sys
import time
import urllib.parse
import dataclasses
import subprocess
import argparse

import requests


# config
rqbit_url = "http://localhost:3030"

###################


def torrenttools(*args):
    args = ["torrenttools"] + list(args)
    return subprocess.check_output(args, text=True).strip()


# cache
torrent_id_by_hash = None
torrent_hash_by_id = None

def get_torrent_id_by_hash():
    torrent_id_by_hash = dict()
    d = requests.get(f"{rqbit_url}/torrents").json()
    for torrent in d["torrents"]:
        hash = torrent["info_hash"].lower()
        torrent_id_by_hash[hash] = torrent["id"]
    return torrent_id_by_hash

def get_torrent_id(hash):
    global torrent_id_by_hash
    if not torrent_id_by_hash:
        torrent_id_by_hash = get_torrent_id_by_hash()
    id = torrent_id_by_hash.get(hash)
    if id is None:
        print(f"error: failed to get id of torrent hash {hash!r}")
    return id

def main():

    global torrent_id_by_hash
    global torrent_hash_by_id

    torrent_id_by_hash = get_torrent_id_by_hash()
    torrent_hash_by_id = dict()
    for hash in torrent_id_by_hash:
        id = torrent_id_by_hash[hash]
        torrent_hash_by_id[id] = hash

    parser = argparse.ArgumentParser()

    # -h is already used by --help
    parser.add_argument('hash', nargs="*")
    #parser.add_argument('--hash', '-H')
    #parser.add_argument('--id', '-i', nargs="*")
    parser.add_argument('--id', '-i', nargs="*", action='extend')
    parser.add_argument('--delete-files', '-D', action="store_true")

    args = parser.parse_args()

    # show rqbit info
    if 1:
        d = requests.get(f"{rqbit_url}/").json()
        print(d["server"], d["version"])
        #sys.exit()

    torrent_id_list = args.id or []

    torrent_id_list += list(map(get_torrent_id, args.hash))

    if not torrent_id_list:
        print("error: no torrents specified")
        parser.print_help()
        sys.exit(1)

    for torrent_id in torrent_id_list:

        if torrent_id is None:
            continue

        #print("todo remove torrent", torrent_id); continue

        torrent_hash = torrent_hash_by_id.get(torrent_id)
        print(f"removing torrent {torrent_id} {torrent_hash}")

        # "POST /torrents/{index}/delete": "Forget about the torrent, remove the files",
        # "POST /torrents/{index}/forget": "Forget about the torrent, keep the files",
        action = "delete" if args.delete_files else "forget"
        url = f"{rqbit_url}/torrents/{torrent_id}/{action}"

        r = requests.post(url).json()
        if r:
            print("response", r)


if __name__ == "__main__":

    main()
