#!/usr/bin/env python3

# move all finished torrents from rtorrent to qbittorrent

# FIXME also copy the priority of files
# example: NSL Archiv
# -> only download: Musik, Hörbücher

# https://pypi.org/project/rtorrent-rpc/
# https://rtorrent-rpc.readthedocs.io/
# https://rtorrent-docs.readthedocs.io/en/latest/cmd-ref.html

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

from rtorrent_rpc import RTorrent
from rtorrent_rpc.helper import parse_comment, parse_tags

import qbittorrentapi


# config
rtorrent_socket = "/media/sdaj/milahu/private/rtorrent/.socket"
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

    with qbittorrentapi.Client(**conn_info) as qbt_client:

        return main_inner(qbt_client)



def main_inner(qbt_client):

    #if qbt_client.torrents_add(urls="...") != "Ok.":
    #    raise Exception("Failed to add torrent.")

    # display qBittorrent info
    if False:
        print(f"qBittorrent: {qbt_client.app.version}")
        print(f"qBittorrent Web API: {qbt_client.app.web_api_version}")
        for k, v in qbt_client.app.build_info.items():
            print(f"{k}: {v}")



    for btih, torrent in get_torrents().items():

        print("torrent", torrent.info_hash, torrent.name)

        # TODO get path of torrent file
        # ~/private/rtorrent/work/81EA96466100E982DCACFD9068C4EABA8FF587A8.torrent
        # session.path.set = /media/sdaj/milahu/private/rtorrent/work
        # load that with qbittorrent

        torrent_file_path = os.path.join(rtorrent_session_path, torrent.info_hash.upper() + ".torrent")
        print("torrent_file_path", torrent_file_path)

        content_path = torrent.directory_base
        print("content_path", content_path)

        content_dir_path = os.path.dirname(content_path)
        print("content_dir_path", content_dir_path)

        # check if qbittorrent already has this torrent
        has_torrent = False
        for torrent2 in qbt_client.torrents_info():
            btih2 = torrent2.info.hash
            if btih.lower() == btih2.lower():
                has_torrent = True
                break

        if has_torrent:
            print("already in qbittorrent", btih)
            print("removing from rtorrent", btih)
            #rtorrent_client.d.stop(btih)
            #rtorrent_client.d.close(btih)
            # d.erase = remove torrent but keep data
            # https://rtorrent-docs.readthedocs.io/en/latest/cmd-ref.html#term-d-erase
            rtorrent_client.d.erase(btih)
            continue

        print("adding to qbittorrent", btih)
        try:
            qbt_client.torrents.add(
                urls = btih, # does this help with empty torrent file?
                torrent_files = torrent_file_path,
                # TODO save_path or download_path
                # save_path	string	Default save path for torrents, separated by slashes
                # download_path ?
                save_path = content_dir_path,
                is_paused = True,
                is_sequential_download = True, # should be default...
                tags = ["rtorrent"],
                # ?
                #download_path: str | None = None,
                #use_download_path: bool | None = None,
                #stop_condition: Literal["MetadataReceived", "FilesChecked"] | None = None,
                #is_stopped: bool | None = None,
            )
        #except qbittorrentapi.exceptions.UnsupportedMediaType415Error as exc:
        except Exception as exc:
            print("FIXME failed to add torrent to qbittorrent", btih, exc)
            # Error: '6B9A2E7BDA1805415272DAADC3015A43DC44F7C1.torrent' is not a valid torrent file.
            # TODO add torrent by btih
            # apparently rtorrent has not-yet downloaded the metadata

        # does "close" delete the torrent from the download list?
        # but it should keep the downloaded files = content
        print("removing from rtorrent", btih)
        rtorrent_client.d.erase(btih)

        print("waiting: qbittorrent is adding torrent ", end="")
        sys.stdout.flush()
        done_start = False
        while not done_start:
            print(".", end="")
            sys.stdout.flush()
            time.sleep(1)
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
        while get_state() in checking_states:
            print(".", end="")
            sys.stdout.flush()
            time.sleep(2)
        print(" ok")



        print("-"*80)



        #break # debug



if __name__ == "__main__":

    main()
