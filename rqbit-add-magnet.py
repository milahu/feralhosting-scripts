#!/usr/bin/env python3

# add torrents to rqbit

# https://github.com/ikatson/rqbit

import os
import sys
import re
import time
import json
import urllib.parse
import dataclasses
import subprocess

import requests


# config
rqbit_url = "http://localhost:3030"
rqbit_url = "http://localhost:3034"

# https://github.com/milahu/deutschetorrents/blob/main/trackerlist.txt
trackerlist = """
udp://45.9.60.30:6969/announce
udp://142.132.183.104:6969/announce
udp://185.216.179.62:25/announce
udp://93.158.213.92:1337/announce
udp://5.255.124.190:6969/announce
http://bt.t-ru.org/ann?magnet
http://bt2.t-ru.org/ann?magnet
http://bt3.t-ru.org/ann?magnet
http://bt4.t-ru.org/ann?magnet
"""

###################


def torrenttools(*args):
    args = ["torrenttools"] + list(args)
    return subprocess.check_output(args, text=True).strip()


import urllib.parse

trackers = re.findall(
    r"(?:^|\n)([a-z]{3,5}://\S+)",
    trackerlist,
    re.S
)

print("trackers")
for t in trackers:
    print(f"  {t}")

def main():

    # show rqbit info
    if 1:
        d = requests.get(f"{rqbit_url}/").json()
        print(d["server"], d["version"])
        #sys.exit()

    if sys.argv[1] == "-f":
        with open(sys.argv[2]) as f:
            sys.argv = sys.argv[:1]
            for l in f.readlines():
                if not l.startswith("magnet:"):
                    continue
                l = l.strip()
                sys.argv.append(l)

    for magnet_link in sys.argv[1:]:

        print("-"*80)

        if not magnet_link.startswith("magnet:?"):
            print("ignoring invalid magnet link", repr(magnet_link))
            continue

        print("magnet_link", repr(magnet_link))

        # add trackers
        for tr in trackers:
            magnet_link += "&tr=" + urllib.parse.quote(tr)

        args = urllib.parse.parse_qsl(magnet_link[len("magnet:?"):])

        #print("args", args); sys.exit()

        btih = None
        btmh = None
        for key, val in args:
            if key != "xt":
                continue
            # xt', 'urn:btih:710b5104de7a91d5d70beed7086a7869fb263be2
            if val.startswith("urn:btih:"):
                btih = val[len("urn:btih:"):]
            else:
                print(f"fixme: failed to parse hash from xt={val}")
                sys.exit()
            break
        if not btih:
            print(f"fixme: failed to parse hash from magnet link", magnet_link)
            sys.exit()

        #btih = torrenttools("show", "infohash", "--protocol", "v1", magnet_link)
        #btmh = torrenttools("show", "infohash", "--protocol", "v2", magnet_link)

        #print("btih", repr(btih))
        #print("btmh", repr(btmh))

        torrent_name = next((val for key, val in args if key == "dn"), None)
        #print("torrent_name", repr(torrent_name))
        if torrent_name is None:
            print("FIXME no torrent_name in magnet link")
            torrent_name = "noname"

        # prefer btih for hybrid torrents
        # because most tools dont support v2 torrents
        if btih:
            content_path = os.environ["HOME"] + "/cas/btih/" + btih + "/" + torrent_name
        elif btmh:
            content_path = os.environ["HOME"] + "/cas/btmh/" + btmh + "/" + torrent_name
        else:
            print("error: failed to get hash of torrent:", magnet_link)
            sys.exit(1)

        # print("torrent", btih, torrent_name)

        # print("content_path", content_path)

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

        print("adding to rqbit") #, btih)

        #r = requests.get(f"{rqbit_url}/torrents", data=payload)
        files = {
            # not working
            # 'file': open(magnet_link, 'rb')
        }
        # https://github.com/ikatson/rqbit#http-api
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
        data = magnet_link
        #data[""] = torrent_file_bytes
        # note: no timeout
        # print("url", repr(url))
        # print("data", json.dumps(data, indent=2))
        try:
            r = requests.post(url, files=files, data=data, timeout=120)
        # rqbit timeout is 600
        except requests.exceptions.ReadTimeout as exc:
            print("FIXME failed to add torrent to rqbit", btih, exc)
            continue
        # except Exception as exc:

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
