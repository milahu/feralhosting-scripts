#!/usr/bin/env python3

# copy all finished torrents from rtorrent to rqbit

# FIXME also copy the priority of files
# example: NSL Archiv
# -> only download: Musik, Hörbücher

# https://pypi.org/project/rtorrent-rpc/
# https://rtorrent-rpc.readthedocs.io/
# https://rtorrent-docs.readthedocs.io/en/latest/cmd-ref.html

# https://github.com/ikatson/rqbit

import os
import sys
import time
import urllib.parse
import dataclasses

from rtorrent_rpc import RTorrent
from rtorrent_rpc.helper import parse_comment, parse_tags

import requests


# config
rtorrent_socket = "/media/sdaj/milahu/private/rtorrent/.socket"
rqbit_url = "http://localhost:3030"

###################


@dataclasses.dataclass
class Torrent:
    name: str
    info_hash: str
    directory_base: str
    tags: set[str]
    comment: str
    is_open: bool
    is_private: bool
    is_complete: bool
    is_hashing: bool
    state: int

    size_bytes: int


def get_torrents() -> dict[str, Torrent]:
    return {
        x[1]: Torrent(
            name=x[0],
            info_hash=x[1],
            directory_base=x[2],
            tags=parse_tags(x[3]),
            comment=parse_comment(x[4]),
            is_open=x[5],
            size_bytes=x[6],
            is_private=x[7],
            state=x[8],
            is_complete=x[9],
            is_hashing=x[10],
        )
        for x in rtorrent_client.d.multicall2(
            "",  # required by rpc, doesn't know why
            "default",
            "d.name=",
            "d.hash=",
            "d.directory_base=",
            "d.custom1=",
            "d.custom2=",
            "d.is_open=",
            "d.size_bytes=",
            "d.is_private=",
            "d.state=",
            "d.complete=",
            "d.hashing=",
        )
    }

@dataclasses.dataclass(kw_only=False)
class File:
    name: str
    size: int


def get_files(info_hash: str) -> list[File]:
    """use json rpc incase there are emoji in filename"""

    files = rtorrent_client.f.multicall(info_hash, "", "f.path=", "f.size_bytes=")

    return [File(name=f[0], size=f[1]) for f in files]


@dataclasses.dataclass
class Tracker:
    info_hash: str
    index: int
    enabled: bool
    url: str


def get_trackers(info_hash: str) -> list[Tracker]:
    return [
        Tracker(
            info_hash=info_hash,
            index=i,
            enabled=x[0],
            url=x[1],
        )
        for i, x in enumerate(rtorrent_client.t.multicall(info_hash, "", "t.is_enabled=", "t.url="))
    ]


################



rtorrent_client = RTorrent(address='scgi://' + rtorrent_socket)

if 0:
    print(rtorrent_client.system_list_methods())
    print(rtorrent_client.rpc.system.listMethods())
    raise 123

# only if your rtorrent support jsonrpc!
#print(rtorrent_client.jsonrpc.call("system.listMethods"))


rtorrent_session_path = rtorrent_client.get_session_path()



def main():

    # show rqbit info
    if 1:
        d = requests.get(f"{rqbit_url}/").json()
        print(d["server"], d["version"])
        #sys.exit()

    for btih, torrent in get_torrents().items():

        print("-"*80)

        print("torrent", torrent.info_hash, torrent.name)

        torrent_file_path = os.path.join(rtorrent_session_path, torrent.info_hash.upper() + ".torrent")
        print("torrent_file_path", torrent_file_path)

        content_path = torrent.directory_base
        print("content_path", content_path)

        content_dir_path = os.path.dirname(content_path)
        print("content_dir_path", content_dir_path)

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
            if False:
                print("removing from rtorrent", btih)
                #rtorrent_client.d.stop(btih)
                #rtorrent_client.d.close(btih)
                # d.erase = remove torrent but keep data
                # https://rtorrent-docs.readthedocs.io/en/latest/cmd-ref.html#term-d-erase
                rtorrent_client.d.erase(btih)
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

        time.sleep(10) # debug

        #break # debug: stop after first



if __name__ == "__main__":

    main()
