#!/usr/bin/env python3

# create and add torrents to rqbit

# https://github.com/ikatson/rqbit

# todo check if torrent file exists

# todo check if torrent was added

# fixme dont create .new-magnet.txt file
# if btih is same

# fixme move content to cas/btih/import sys
# try to fetch torrent
# based on 1337x.to
# all return html (on error)
# Invalid torrent file format
# todo try catch
def get_torrent_url_list(btih):
  btih = btih.upper()
  return [
    f"http://itorrents.org/torrent/{btih}.torrent",
    f"http://torrage.info/torrent.php?h={btih}",
    f"http://btcache.me/torrent/{btih}",
  ]
btih = "09efdae290d3e1268167f5909db4c1ad67996f7a"
btih = "06ba2177aefc58d435051e7682b04efa289a6d8a"
btih = "054de0a7e97df6bcd9a7b9a5a183e834f5d1fa44"
btih = "fd790fe74d263325b4106e14fb04635e54617f04"
if 0:
  for u in get_torrent_url_list(btih):
    print(u)
  import sys
  sys.exit()

print("import...")
import os
import sys
import time
import re
import shutil
import urllib.parse
import dataclasses
import subprocess
import json
import pwd
import grp
import stat

print("import requests")
#import requests
print("import torf")
from torf import Torrent
import qbittorrentapi
import torf
import psutil



# config

new_magnets_path = "~/new-magnets.txt"

cas_config_path = os.path.expanduser("~/.config/cas.json")
# example config:
"""
{
  "dirs": [
    "/run/media/user/WSC14YZM_8TB/cas"
  ]
}
"""

ignore_mountpoint_list = (
    '/nix/store',
    '/boot',
)

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

# https://github.com/milahu/deutschetorrents/blob/main/trackerlist.txt
# udp://142.132.183.104:6969/announce # not working
# udp://5.255.124.190:6969/announce # no peers
# udp://45.9.60.30:6969/announce # high latency: 200ms
trackerlist = """
udp://185.216.179.62:25/announce
udp://93.158.213.92:1337/announce
udp://107.189.2.131:1337/announce
"""


# https://github.com/ngosang/trackerslist
# https://github.com/ngosang/trackerslist/blob/master/trackers_all_ip.txt
# todo absolute path
trackerlist_all_path = "~/src/trackerslist/trackers_all_ip.txt"
trackerlist_all_path = os.path.expanduser(trackerlist_all_path)

trackers_ru = [
    "http://bt.t-ru.org/ann?magnet",
    "http://bt2.t-ru.org/ann?magnet",
    "http://bt3.t-ru.org/ann?magnet",
    "http://bt4.t-ru.org/ann?magnet",
]

# todo loop all piece sizes
# to brute force the original btih
# https://www.reddit.com/r/torrents/comments/dzxfz1/2019_whats_ideal_piece_size/
piece_size_list = [
    4*1024*1024, # 4 MiB
    8*1024*1024, # 8 MiB
    2*1024*1024, # 2 MiB
    16*1024*1024, # 16 MiB
    1*1024*1024, # 1 MiB
    #32*1024*1024, # 32 MiB
    512*1024, # 512 KiB
    #64*1024*1024, # 64 MiB
    16*1024, # 16 KiB
]



###################



is_root_user = True
assert os.getuid() == 0, f"must be root. hint: sudo {sys.argv[0]}"



with open(cas_config_path) as f:
    cas_config = json.load(f)
cas_path_list = cas_config["dirs"]

with open(qbt_config_path) as f:
    conn_info = json.load(f)

r"""
def torrenttools(*args):
    args = ["torrenttools"] + list(args)
    return subprocess.check_output(args, text=True).strip()
"""

def parse_trackerlist(trackerlist):
  return re.findall(
    r"(?:^|\n)([a-z]{3,5}://\S+)",
    trackerlist,
    re.S
  )

trackers = parse_trackerlist(trackerlist)

print("trackers")
for t in trackers:
    print(f"  {t}")

with open(trackerlist_all_path) as f:
  trackers_all = parse_trackerlist(f.read())

import os



# https://stackoverflow.com/a/1392549/29400002
def get_size(start_path = '.'):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            # skip if it is symbolic link
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    return total_size

# print(get_size(), 'bytes')

"""
content_path = "Some.Content"
content_size = get_size(content_path)
piece_size = torf.calculate_piece_size(content_size)
"""

def get_torrent_url_list(btih):
  return []

def format_dev(dev):
    minor = dev & 0xff
    major = dev >> 8 & 0xff
    return f"{major},{minor}"


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
            os.chmod(
                p,
                mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH),
                follow_symlinks=False,
            )

        # "chmod 0777" for dirs
        # make all dirs world-writable
        for name in dirs:
            p = os.path.join(root, name)
            os.chmod(p, 0o0777, follow_symlinks=False)

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


def main():
    with qbittorrentapi.Client(**conn_info) as qbt_client:
        return main_inner(qbt_client)


def main_inner(qbt_client):

    magnet_link_list = []

    if 1:
        print(f"qBittorrent: {qbt_client.app.version}")
        print(f"qBittorrent Web API: {qbt_client.app.web_api_version}")
        #for k, v in qbt_client.app.build_info.items():
        #    print(f"{k}: {v}")

    for content_path in sys.argv[1:]:

        print("-"*40)

        content_path = os.path.normpath(content_path)

        if not os.path.exists(content_path):
            print(f"error: no such file: {content_path}")
            continue

        print("content_path", content_path)

        new_magnet_path = content_path + ".new-magnet.txt"
        if os.path.exists(new_magnet_path):
            # fixme can be missing in rqbit
# todo check if rqbit has this torrent
            print("has new torrent")
            continue

        if content_path.lower().endswith(".torrent"):
            print("skipping .torrent file")
            continue

        if content_path.lower().endswith(".new-magnet.txt"):
            print("skipping .new-magnet.txt file")
            continue

        btih_expected = None

        # todo more generic check
        #if content_path.startswith("cas/btih/"):
        if content_path.split("/")[-4:-2] == ["cas", "btih"]:
            btih_expected = content_path.split("/")[-2]
            print("btih_expected", btih_expected)
            if len(btih_expected) != 40:
                print("error: failed to parse btih from content_path")
                continue
            p = ".cache/rqbit/" + btih_expected.lower() + ".torrent"
            if os.path.exists(p):
# todo check if rqbit has this torrent
                print("info: torrent exists", p)
                continue
            magnet_expected = "magnet:?xt=urn:btih:" + btih_expected + "&dn=" + urllib.parse.quote(os.path.basename(content_path))
            print("magnet_expected", magnet_expected)
            # add trackers
            for tr in trackers:
                magnet_expected += "&tr=" + urllib.parse.quote(tr)
            for tr in trackers_ru:
                magnet_expected += "&tr=" + urllib.parse.quote(tr)
            for tr in trackers_all:
                magnet_expected += "&tr=" + urllib.parse.quote(tr)
            # todo try to add magnet_expected
            r"""
            # timeout = no peer was found
            # data=data
            post_data = magnet_expected
            get_data = dict(
              #overwrite = "false",
              overwrite = "true", # fix: Error: error creating ".../file.txt" Caused by: File exists (os error 17)
              # the regular expression string to match filenames
              #only_files_regex = "",
              # the folder to download to. If not specified, defaults to the one that rqbit server started with
              output_folder = content_path,
              # if you want to just list the files in the torrent instead of downloading
              list_only = "false"
            )
            url = f"{rqbit_url}/torrents?" + urllib.parse.urlencode(get_data)
            # with open(torrent_file_path, 'rb') as f:
            #     torrent_file_bytes = f.read()
            # post_data = torrent_file_bytes
            try:
                r = requests.post(url, data=post_data, timeout=30)
                print("ok: got metadata from peers")
                continue
            except Exception as exc:
                # timeout
                print("failed to fetch metadata from peers")
            """

# why re.sub
        torrent_file_path = re.sub(r"[\\/]+$", r"", content_path) + ".torrent"
        print("torrent_file_path", torrent_file_path)

        t = None

        if os.path.exists(torrent_file_path):
            # TODO try catch
            print("using existing torrent file")
            # TODO verify contents
            try:
                t = Torrent.read(torrent_file_path)
            except Exception as exc:
                print(exc)
                print("removing", torrent_file_path)
                os.unlink(torrent_file_path)
            if btih_expected and t and t.infohash != btih_expected:
                print("removing torrent file with wrong btih")
                os.unlink(torrent_file_path)
                t = None

        torrent_url_list = []
        if not t and btih_expected:
            torrent_url_list = get_torrent_url_list(btih_expected)
        for torrent_url in torrent_url_list:
            try:
                r = requests.get(torrent_url, timeout=30)
                with open(torrent_file_path, "wb") as f:
                    f.write(r.content)
                t = Torrent.read(torrent_file_path)
                """
                try:
                    t = Torrent.read(torrent_file_path)
                except Exception as exc:
                    print(exc)
                    print("removing", torrent_file_path)
                    os.unlink(torrent_file_path)
                """
            except Exception as exc:
                print("fail download torrent_url", torrent_url, exc)

        if get_size(content_path) == 0:
            print("skipping empty content_path", content_path)
            continue

        #if not os.path.exists(torrent_file_path):
        _piece_size_list = []
        if not t:
            # no. this is the apparent size
            # content_size = shutil.disk_usage(content_path).used
            # content_size = get_size(content_path)
            """
            content_size = Torrent(content_path).size
            print("content_size", content_size)
            _default_piece_size = Torrent.calculate_piece_size(content_size)
            default_piece_size = Torrent(content_path).piece_size
            assert _default_piece_size == default_piece_size
            """
            default_piece_size = Torrent(content_path).piece_size
            default_piece_size_1 = Torrent(content_path, piece_size_min=4*1024*1024).piece_size
            print("default_piece_size", default_piece_size)

            if default_piece_size == 0:
                # this would throw
                # torf._errors.PieceSizeError: Piece size must be divisible by 16 KiB: 0
                # in t = Torrent(...)
                print("skipping empty content_path", content_path)
                continue

            _piece_size_list = (
                [] +
                [default_piece_size_1] +
                [default_piece_size] +
                list(filter(lambda s: s != default_piece_size, piece_size_list)) +
                # [default_piece_size] +
                []
            )
        for piece_size in _piece_size_list:
            print("creating new torrent file with piece_size", piece_size)
            t = Torrent(
                path=content_path,
                trackers=trackers,
                creation_date=None,
                created_by=None,
                # todo loop all piece sizes
                # to brute force the original btih
                #piece_size=None,
                piece_size=piece_size,
                #piece_size_min=4*1024*1024,
                randomize_infohash=False,
            )
            t.generate()
            btih = t.infohash
            print("btih", btih)
            if os.path.exists(f".cache/rqbit/{btih}.torrent"):
                # already in rqbit
                break
            if not btih_expected:
                break
                # use default piece size
            if btih == btih_expected:
                print("found expected btih with piece_size", piece_size)
                break
            t = None

        if not t:
            # failed to guess btih
            # create new torrent
            t = Torrent(
                path=content_path,
                trackers=trackers,
                creation_date=None,
                created_by=None,
                #piece_size=None,
                piece_size_min=4*1024*1024,
                randomize_infohash=False,
            )
            t.generate()
            btih = t.infohash
            print("btih", btih)
            if not os.path.exists(f".cache/rqbit/{btih}.torrent"):
                magnet_link = str(t.magnet())
                p = new_magnets_path
                p = os.path.expanduser(p)
                with open(p, "a") as f:
                    f.write(magnet_link + "\n")
            if not os.path.exists(new_magnet_path):
                with open(new_magnet_path, "w") as f:
                    f.write(str(t.magnet()) + "\n")

        # t.metainfo['more stuff']

        # btih = torrenttools("show", "infohash", "--protocol", "v1", torrent_file_path)
        # btmh = torrenttools("show", "infohash", "--protocol", "v2", torrent_file_path)
        btih = t.infohash
        print("btih", repr(btih))
        assert len(btih) == 40
        # assert len(btmh) == 64

        # add piece size to magnet link
        # to help creating torrent
        # from existing files
        s = f"&piece_size={t.piece_size}"
        magnet_link = str(t.magnet()) + s

        print("magnet", magnet_link)

        magnet_link_list.append(magnet_link)

        p = new_magnets_path
        p = os.path.expanduser(p)
        with open(p, "a") as f:
            f.write(magnet_link + "\n")

        """
        if btih_expected and btih != btih_expected:
            # todo? keep new torrent
            print("error: failed to re-create btih", btih_expected)
            continue
        """
        # keep new torrent

        if btih_expected and not os.path.exists(new_magnet_path):
            with open(new_magnet_path, "w") as f:
                f.write(str(t.magnet()) + "\n")

        """
        p = ".cache/rqbit/" + btih.lower() + ".torrent"
        if os.path.exists(p):
            # todo check if rqbit has this torrent
            print("info: torrent exists", p)
            continue
        """

        if not os.path.exists(torrent_file_path):
            t.write(torrent_file_path)

        #print("btmh", repr(btmh))
        btmh = None # FIXME

        #torrent_name = torrenttools("show", "name", torrent_file_path)
        torrent_name = t.name

        src_content_path = content_path

        src_dev = os.stat(src_content_path).st_dev
        cas_path = None
        for path in cas_path_list:
            print(f"cas path {path}")
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
            content_path = cas_path + "/btih/" + btih + "/" + torrent_name
        elif btmh:
            content_path = cas_path + "/btmh/" + btmh + "/" + torrent_name
        else:
            print("error: failed to get hash of torrent:", torrent_file_path)
            sys.exit(1)

        print(f"mkdir -p {os.path.dirname(content_path)!r}")
        os.makedirs(os.path.dirname(content_path), exist_ok=True)

        print(f"chmod 0777 {os.path.dirname(content_path)!r}")
        os.chmod(os.path.dirname(content_path), 0o0777, follow_symlinks=False)

        # todo more generic check
        #if content_path.startswith("cas/btih/"):
        #if True:
        if btih_expected and btih != btih_expected:
            # keep src
            # fixme dst exists
            if os.path.exists(content_path):
                shutil.move(content_path, content_path + ".trash" + str(int(time.time())))
            print(f"cp -rl {src_content_path!r} {content_path!r}")
            if os.path.isdir(src_content_path):
                shutil.copytree(src_content_path, content_path, copy_function=os.link)
            else:
                os.link(src_content_path, content_path)
        # why not
        else:
            if os.path.exists(content_path):
                print(f"error: content_path exists: {content_path!r}")
                # TODO better
                continue
                #sys.exit(1)
            print(f"mv {src_content_path!r} {content_path!r}")
            shutil.move(src_content_path, content_path)

        if is_root_user:
            # make the content files read-only
            protect_tree(content_path)

        assert os.path.exists(torrent_file_path)

        src_torrent_file_path = torrent_file_path
        #torrent_file_path = content_path + ".torrent"
        # torrent_file_path is compatible with the "cas" parameter at
        # https://github.com/bittorrent/bittorrent.org/pull/171
        torrent_file_path = os.path.dirname(content_path) + ".torrent"

        if os.path.exists(torrent_file_path):
            print(f"error: torrent_file_path exists: {torrent_file_path!r}")
            # TODO better
            #sys.exit(1)
        if not os.path.exists(torrent_file_path):
            print(f"mv {src_torrent_file_path!r} {torrent_file_path!r}")
            shutil.move(src_torrent_file_path, torrent_file_path)

        print("torrent", btih, torrent_name)

        print("content_path", content_path)

        content_dir_path = os.path.dirname(content_path)
        print("content_dir_path", content_dir_path)

        print("magnet", magnet_link)

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

        #continue

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
                try:
                    if torrent2.info.hash.lower() == btih.lower():
                        return torrent2.state
                except AttributeError:
                    # AttributeError: 'Torrent' object has no attribute 'info'
                    # AttributeError: 'TorrentDictionary' instance has no attribute 'hash'
                    pass

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
        for _ in range(120): # 120 * 5 = 600 = 10 minutes
            if not get_state() in checking_states:
                break
            print(".", end="")
            sys.stdout.flush()
            time.sleep(5)
        print(" ok")



        print("state", get_state())

        # qBittorrent -> settings -> downloads -> stop torrent: done checking files
        # re-start the torrent after checking
        # see also: is_uploading
        seeding_states = (
            "stalledUP",
            "queuedUP",
            "forcedUP",
            "uploading",
            # "pausedUP", # not seeding # was renamed to "stoppedUP"
            # "stoppedUP", # not seeding
        )
        print("waiting: qbittorrent is starting torrent ", end="")
        sys.stdout.flush()
        done_start = False
        # while not done_start:
        for _ in range(12):
            if get_state() in seeding_states:
                break
            print(f" (state={get_state()}) ", end="")
            print(".", end="")
            sys.stdout.flush()
            # time.sleep(5)
            for torrent2 in qbt_client.torrents.info():
                try:
                    btih2 = torrent2.info.hash
                except AttributeError:
                    # 'TorrentDictionary' instance has no attribute 'hash'
                    continue
                if btih.lower() == btih2.lower():
                    # torrent2.resume()
                    torrent2.start()
                    break
            time.sleep(5)
        print(" ok")



        # break # debug



    print()

    for m in magnet_link_list:
        print(m)



if __name__ == "__main__":

    main()
