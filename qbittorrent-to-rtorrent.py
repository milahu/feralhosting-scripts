#!/usr/bin/env python3

# copy all finished torrents from qbittorrent to rtorrent

# note: copy, not move

# FIXME also copy the priority of files
# example: NSL Archiv
# -> only download: Musik, Hörbücher

# https://pypi.org/project/rtorrent-rpc/
# https://rtorrent-rpc.readthedocs.io/
# https://rtorrent-docs.readthedocs.io/en/latest/cmd-ref.html
# https://github.com/trim21/rtorrent-rpc/raw/master/rtorrent_rpc/__init__.py

# https://github.com/rmartin16/qbittorrent-api
# https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)
# https://qbittorrent-api.readthedocs.io/en/latest/
# https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)#set-torrent-location
# https://qbittorrent-api.readthedocs.io/en/latest/apidoc/torrents.html#qbittorrentapi.torrents.TorrentDictionary.set_location
# https://github.com/rmartin16/qbittorrent-api/raw/main/src/qbittorrentapi/torrents.py

import os
import sys
import time
import tempfile
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



    for torrent in qbt_client.torrents_info():

        btih = torrent.info.hash.lower()

        """
        # debug
        debug_btih = "beef..."
        if btih != debug_btih:
            continue
        """

        # check if torrent already is in rtorrent
        has_torrent = False
        for btih2, _torrent2 in get_torrents().items():
            if btih == btih2.lower():
                has_torrent = True
                break
        if has_torrent:
            continue

        #print("torrent", torrent.info_hash, torrent.name)
        print("torrent", torrent.info.hash, torrent.info.name)

        # usually, save_path is the parent directory of content_path
        # for single-file in single-directory torrents
        #   content_path is file_path
        #   save_path is dirname(directory_path)
        print("  save_path     ", torrent.save_path)
        print("  content_path  ", torrent.content_path)

        # get the actual content path
        content_path_2 = torrent.save_path + torrent.content_path[len(torrent.save_path):].split("/")[0]
        assert os.path.exists(content_path_2), f"missing content_path_2 {content_path_2}"
        if torrent.content_path != content_path_2:
            print("  content_path_2", content_path_2)

        #break # debug

        # no. this is content, not metadata
        #torrent_content_files = qbt_client.torrents.files(torrent_hash=btih)
        #print("torrent_files", torrent_files)

        # FIXME This method was introduced with qBittorrent v4.5.0 (Web API v2.8.14).
        #torrent_bytes = qbt_client.torrents.export(torrent_hash=btih)
        #torrent_bytes = qbt_client._client.torrents_export(torrent_hash=btih)
        #torrent_bytes = qbt_client.torrents.export(torrent_hash=torrent.info.hash)
        torrent_bytes = qbt_client.torrents_export(torrent_hash=torrent.info.hash)

        #directory_base = torrent.content_path
        directory_base = content_path_2
        #if os.path.isfile(torrent.content_path):
        #    directory_base = os.path.dirname(torrent.content_path)
        if os.path.isfile(directory_base):
            assert torrent.save_path == os.path.dirname(directory_base), f"{torrent.save_path} != {os.path.dirname(directory_base)}"
            directory_base = torrent.save_path
            #directory_base = os.path.dirname(directory_base)
        # no. this breaks with single-file no-directory torrents
        #directory_base = content_path_2
        # no. this works with single-file no-directory torrents
        # but breaks with multi-file torrents
        #directory_base = torrent.save_path

        print("  directory_base", directory_base)

        if torrent_bytes is None:
            torrent_path = os.environ["HOME"] + "/.local/share/qBittorrent/BT_backup/" + btih + ".torrent"
            print("  torrent_path  ", torrent_path)
            if os.path.exists(torrent_path):
                with open(torrent_path, "rb") as f:
                    torrent_bytes = f.read()

        if torrent_bytes:
            try:
                # add torrent to rtorrent in started state
                # https://rtorrent-docs.readthedocs.io/en/latest/cmd-ref.html#load-commands
                # rtorrent_client.rpc.load.raw_start_verbose(*params)
                rtorrent_client.add_torrent_by_file(
                    content=torrent_bytes,
                    #directory_base=os.path.dirname(torrent.content_path),
                    directory_base=directory_base,
                    tags=["qbt"],
                    #extras=[],
                )
            #except BrokenPipeError as exc:
            except Exception as exc:
                print(f"add_torrent_by_file failed: {exc}")
                print("adding torrent via tempfile")
                # add_torrent_by_file fails on large torrent files
                # add torrent via tempfile
                with tempfile.NamedTemporaryFile(mode='w+b', prefix="rtorrent-", suffix=".torrent") as f:
                    f.write(torrent_bytes)
                    tempfile_path = f.name
                    params = [
                        "",
                        tempfile_path,
                        'd.tied_to_file.set=""',
                        f'd.directory_base.set="{directory_base}"',
                        #*_real_iterator_of_str(extras),
                    ]
                    rtorrent_client.rpc.load.start_verbose(*params)

        else:
            # use magnet link
            magnet_link = torrent.info.magnet_uri
            #directory_base = os.path.dirname(torrent.content_path)
            params = [
                "",
                magnet_link,
                'd.tied_to_file.set=""',
                f'd.directory_base.set="{directory_base}"',
                #*_real_iterator_of_str(extras),
            ]
            rtorrent_client.rpc.load.start_verbose(*params)

        # sleep?

        # set download path
        #r.d.directory.set(btih, torrent.content_path)

        # start torrent
        #rtorrent_client.d.start(btih)

        #if os.path.isfile(torrent.content_path):
        #    print("TODO check single file torrent")
        #    break # debug

        # break # debug: stop after first torrent

        # TODO wait for rtorrent to check files, then continue

        import time
        time.sleep(10) # debug

        continue

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
