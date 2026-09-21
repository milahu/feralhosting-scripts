#!/usr/bin/env python3

# add torrents to rqbit

# https://github.com/ikatson/rqbit

import os
import sys
import time
import urllib.parse
import dataclasses
import subprocess

import requests
import torf
from torf import Torrent


# config
rqbit_url = "http://localhost:3030"
rqbit_url = "http://localhost:3034"

###################


r"""
def torrenttools(*args):
    args = ["torrenttools"] + list(args)
    return subprocess.check_output(args, text=True).strip()
"""


def main():

    # show rqbit info
    if 1:
        d = requests.get(f"{rqbit_url}/").json()
        print(d["server"], d["version"])
        #sys.exit()

    for torrent_file_path in sys.argv[1:]:

        print("-"*80)

        if not os.path.exists(torrent_file_path):
            print(f"error: no such file: {torrent_file_path}")
            continue

        print("torrent_file_path", torrent_file_path)

        try:
            t = Torrent.read(torrent_file_path)
        #except torf._errors.BdecodeError as exc:
        except (torf._errors.BdecodeError, torf._errors.MetainfoError) as exc:
            print(f"error: invalid torrent file: {torrent_file_path} - {exc}")
            os.rename(torrent_file_path, torrent_file_path + ".broken")
            continue
        # t.metainfo['more stuff']

        # btih = torrenttools("show", "infohash", "--protocol", "v1", torrent_file_path)
        # btmh = torrenttools("show", "infohash", "--protocol", "v2", torrent_file_path)
        btih = t.infohash
        print("btih", repr(btih))
        assert len(btih) == 40
        # assert len(btmh) == 64

        #print("btmh", repr(btmh))
        btmh = None # FIXME

        #torrent_name = torrenttools("show", "name", torrent_file_path)
        torrent_name = t.name

        # prefer btih for hybrid torrents
        # because most tools dont support v2 torrents
        if btih:
            content_path = os.environ["HOME"] + "/cas/btih/" + btih + "/" + torrent_name
        elif btmh:
            content_path = os.environ["HOME"] + "/cas/btmh/" + btmh + "/" + torrent_name
        else:
            print("error: failed to get hash of torrent:", torrent_file_path)
            sys.exit(1)

        print("torrent", btih, torrent_name)

        print("content_path", content_path)

        #content_dir_path = os.path.dirname(content_path)
        #print("content_dir_path", content_dir_path)

        # check if rqbit already has this torrent
        has_torrent = False
        d = requests.get(f"{rqbit_url}/torrents").json()
        for torrent2 in d["torrents"]:
            btih2 = torrent2["info_hash"]
            if btih.lower() == btih2.lower():
                has_torrent = True
                break

        if has_torrent:
            print("already in rqbit", btih)
            continue

        print("adding to rqbit", btih)

        #r = requests.get(f"{rqbit_url}/torrents", data=payload)
        files = {
            # not working
            # 'file': open(torrent_file_path, 'rb')
        }
        data = dict(
          #overwrite = "false",
          overwrite = "true", # fix: Error: error creating ".../file.txt" Caused by: File exists (os error 17)
          # the regular expression string to match filenames
          #only_files_regex = "",
          # the folder to download to. If not specified, defaults to the one that rqbit server started with
          output_folder = content_path,
          # if you want to just list the files in the torrent instead of downloading
          list_only = "false"
        )
        url = f"{rqbit_url}/torrents?" + urllib.parse.urlencode(data)
        with open(torrent_file_path, 'rb') as f:
            torrent_file_bytes = f.read()
        #data[""] = torrent_file_bytes
        # fixme this can hang
        # add a retry loop?
        r = requests.post(url, files=files, data=torrent_file_bytes)

        """
        except Exception as exc:
            print("FIXME failed to add torrent to rqbit", btih, exc)
        """

        if 0:
            # does "close" delete the torrent from the download list?
            # but it should keep the downloaded files = content
            print("removing from rtorrent", btih)
            rtorrent_client.d.erase(btih)

        # TODO optional: wait for rqbit to check files with timeout

        #time.sleep(10) # debug

        #break # debug: stop after first



if __name__ == "__main__":

    main()
