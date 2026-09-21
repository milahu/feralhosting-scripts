#!/usr/bin/env python3

# TODO create symlink
# from the non-CAS path to the CAS path

# TODO also move extra files which are not part of the torrent
# but are in the same directory
# and do not belong to another torrent

# TODO also write all torrent files to the CAS
# qbittorrent-save-torrents.py

# https://github.com/milahu/cas_torrent/raw/main/scripts/qbittorrent-move-to-cas.py

# move all finished torrents to ~/cas/btih/{btih}

# https://github.com/rmartin16/qbittorrent-api
# https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)
# https://qbittorrent-api.readthedocs.io/en/latest/
# https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)#set-torrent-location
# https://qbittorrent-api.readthedocs.io/en/latest/apidoc/torrents.html#qbittorrentapi.torrents.TorrentDictionary.set_location
# https://github.com/rmartin16/qbittorrent-api/raw/main/src/qbittorrentapi/torrents.py

import os
import sys
import time
import json
import pwd
import grp
import stat
import subprocess

import qbittorrentapi



is_root_user = True
assert os.getuid() == 0, f"must be root. hint: sudo {sys.argv[0]}"



# config
home_dir = os.environ["HOME"]
#src_dir = home_dir + "/private/qbittorrent/data"
src_dir = home_dir + "/Downloads/torrent/content"

# dst_dir = home_dir + "/cas"
# dst_dir = "/media/ZYD82805_24TB/cas"
# # TODO use ~/.config/cas.json
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
# qbt_config_path = os.path.expanduser("~/.config/qbittorrentapi-no-vpn.json")
if len(sys.argv) > 1:
    qbt_config_path = sys.argv[1]


# def protect_tree(path: str, *, owner="nobody", group="nogroup"):
def protect_tree(path: str, *, owner="root", group="root"):
    "make files read-only"
    # Look up uid/gid (skip if account doesn't exist)
    try:
        uid = pwd.getpwnam(owner).pw_uid
        gid = grp.getgrnam(group).gr_gid
    except KeyError:
        uid = gid = None
        if owner == "root": uid = 0
        if group == "root": gid = 0

    # print(f"protect_tree: uid={uid} gid={gid}")

    # Walk bottom-up so files are handled before directories
    for root, dirs, files in os.walk(path, topdown=False):
        # Remove write bits of files
        # make all files read-only
        for name in files:
            p = os.path.join(root, name)
            mode = os.stat(p, follow_symlinks=False).st_mode
            try:
                os.chmod(
                    p,
                    mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH),
                    follow_symlinks=False,
                )
            except PermissionError:
                # file is immutable
                pass

        # "chmod 0777" for dirs
        # make all dirs world-writable
        for name in dirs:
            p = os.path.join(root, name)
            os.chmod(p, 0o0777, follow_symlinks=False)

        # make files mutable
        for name in files:
            p = os.path.join(root, name)
            subprocess.run(["chattr", "-i", p], check=True)

        # Change owner of files and dirs
        # make all files and dirs owned by root
        if uid is not None:
            for name in files + dirs:
                p = os.path.join(root, name)
                os.chown(p, uid, gid, follow_symlinks=False)

        # make files immutable
        for name in files:
            p = os.path.join(root, name)
            subprocess.run(["chattr", "+i", p], check=True)

        # "chmod 0777" for root dir
        os.chmod(root, 0o0777, follow_symlinks=False)

        # Change owner of root dir
        if uid is not None:
            os.chown(root, uid, gid, follow_symlinks=False)


with open(cas_config_path) as f:
    cas_config = json.load(f)
cas_path_list = cas_config["dirs"]


with open(qbt_config_path) as f:
    conn_info = json.load(f)

with qbittorrentapi.Client(**conn_info) as qbt_client:

    #if qbt_client.torrents_add(urls="...") != "Ok.":
    #    raise Exception("Failed to add torrent.")

    # display qBittorrent info
    if False:
        print(f"qBittorrent: {qbt_client.app.version}")
        print(f"qBittorrent Web API: {qbt_client.app.web_api_version}")
        for k, v in qbt_client.app.build_info.items():
            print(f"{k}: {v}")

    # state
    finished_states = (
        "uploading", # Torrent is being seeded and data is being transferred
        "pausedUP",  # Torrent is paused and has finished downloading
        "queuedUP",  # Queuing is enabled and torrent is queued for upload
        "stalledUP", # Torrent is being seeded, but no connection were made
        "forcedUP",  # Torrent is forced to uploading and ignore queue limit
    )

    for torrent in qbt_client.torrents_info():

        #print(f"torrent {torrent.hash} {torrent.name} {torrent.state} {torrent.content_path}")

        # only move finished torrents
        if not torrent.state in finished_states:
            continue

        if not torrent.content_path:
            continue

        if not torrent.content_path.startswith(torrent.save_path):
            print("  save   ", torrent.save_path)
            print("  content", torrent.content_path)

        assert torrent.content_path.startswith(torrent.save_path)

        # usually, save_path is the parent directory of content_path
        # for single-file in single-directory torrents
        #   content_path is file_path
        #   save_path is dirname(directory_path)
        src = torrent.save_path
        src2 = torrent.content_path

        # if src != "/media/ZYD82805_24TB/cas/todo":
        if 0:
            print(f"FIXME src={src}")
            continue

        # if "/cas/btih/" in src or "/cas/btmh/" in src:
        if 0:
            # already in a CAS filesystem
            continue

        # get the actual content path
        # src2 = torrent.save_path + torrent.content_path[len(torrent.save_path):].split("/")[0]

        '''
        #if os.path.dirname(torrent.content_path) + "/" != torrent.save_path:
        if os.path.dirname(src2) + "/" != src:
            print('FIXME dirname(src2) + "/" != src')
            print("  src ", src)
            print("  src2", src2)
            sys.exit(1)
        '''

        # can be truncated v2 hash
        #btih = torrent.info.hash
        # ('infohash_v1', '9054154f3b6e48d61b24108c113b21aedbba02fc')
        # ('infohash_v2', '275eca76b77c688c501e2ffab447e7d60facb472d2537c47f07b6976d69f437a')
        btih = torrent.infohash_v1
        assert len(btih) == 40, f"non-v1 btih: {btih}"

        # TODO support v2/hybrid torrents
        btmh = None

        #torrent_name = torrenttools("show", "name", torrent_file_path)
        torrent_name = torrent.name

        #print(dir(torrent))
        #print(dir(torrent.info))
        #print(torrent.items())
        #print(torrent._torrent_hash) # can be truncated v2 hash
        #print("v1", torrent.infohash_v1)
        #print("v2", torrent.infohash_v2)

        # debug
        debug_btih = None
        # debug_btih = "c2f0b5d26a886ba12f7f667d69c0459056dcda9b"
        if debug_btih and btih != debug_btih:
            continue

        # # FIXME try to keep the files on the same filesystem
        # dst = dst_dir + "/btih/" + btih.lower()
        # # dst2 = dst_dir + "/btih/" + btih.lower() + src2[len(src_dir):]
        # dst2 = dst + src2[len(src):]



        # src_content_path = src # ?
        src_content_path = src2

        src_dev = os.stat(src_content_path).st_dev
        cas_path = None
        for path in cas_path_list:
            # print(f"cas path {path}")
            try:
                dst_dev = os.stat(path).st_dev
            except FileNotFoundError:
                continue
            if src_dev == dst_dev:
                cas_path = path
                break
        if not cas_path:
            print(f"not found cas path on the same filesystem")
            # try to use the same device as src_content_path
            # this assumes that no symlinks are used...
            for p in psutil.disk_partitions():
                # print(p.mountpoint, psutil.disk_usage(p.mountpoint).percent)
                if p.mountpoint in ignore_mountpoint_list: continue
                print(f"p.mountpoint {p.mountpoint!r}")
                dst_dev = os.stat(p.mountpoint).st_dev
                if src_dev == dst_dev:
                    _cas_path = os.path.normpath(p.mountpoint + "/cas")
                    if os.path.exists(_cas_path):
                        cas_path = _cas_path
                        break
        if not cas_path:
            # print(f"error: not found cas_path for src_content_path {src_content_path!r}. src_dev {src_dev} = {format_dev(src_dev)}")
            # TODO print a list of mountpoints
            # sys.exit(1)
            cas_path = cas_path_list[0]
            print(f"using the first cas_path {cas_path!r}")

        # prefer btih for hybrid torrents
        # because most tools dont support v2 torrents
        if btih:
            # content_path = cas_path + "/btih/" + btih + "/" + torrent_name
            dst = cas_path + "/btih/" + btih
        elif btmh:
            # content_path = cas_path + "/btmh/" + btmh + "/" + torrent_name
            dst = cas_path + "/btmh/" + btmh
        else:
            print("error: failed to get hash of torrent:", torrent_file_path)
            sys.exit(1)

        dst2 = dst + src2[len(src):]

        if 0:
            print("  src ", src)
            print("  src2", src2)
            print("  dst ", dst)
            print("  dst2", dst2)

        #sys.exit(1)

        #if torrent.save_path == dst + "/":
        if src == dst:
            # nothing to do
            continue

        print()
        print(f"torrent {torrent.hash} {torrent.name} {torrent.state} {torrent.content_path}")

        # print("  save   ", torrent.save_path)
        print("  src    ", src)
        print("  dst    ", dst)
        # print("  content", torrent.content_path)
        # print("  src2   ", src2)


        if src.split("/")[:4] != dst.split("/")[:4]:
            print(f"FIXME keep files on the same filesystem")

        # input("hit enter to move: ")

        wait_for_check = False

        if os.path.exists(dst) and len(os.listdir(dst)) > 0:
            # FIXME avoid checking files
            # https://github.com/qbittorrent/qBittorrent/issues/19399
            # workaround: close qbt, move files, start qbt, wait for torrents to throw error, set location -> no recheck
            # maybe: instead of close/start qbt, stop/start the torrent
            print("note: dst exists. qbittorrent will check files.", dst)
            wait_for_check = True

        os.makedirs(os.path.dirname(dst), exist_ok=True)

        # move torrent files
        # https://github.com/rmartin16/qbittorrent-api/raw/main/src/qbittorrentapi/torrents.py
        try:
            torrent.set_location(dst)
        except Exception as exc:
            print(f"FIXME torrent.set_location failed: {type(exc).__name__}: {exc}")
            print(f"hint: sudo chmod 0777 {cas_path}/btih")
            raise
            time.sleep(5)
            continue
        time.sleep(1)

        # FIXME wait until move is complete across different filesystems
        # wait until all source files have disappeared
        # and/or until all destination files have appeared
        if is_root_user:
            # make the content files read-only
            protect_tree(dst)

        if not wait_for_check:
            continue

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



# print(f"TODO make sure all torrents are finished, then ...")
# print(f"TODO rm -rf {src_dir}/*")
