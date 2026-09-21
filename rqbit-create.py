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

print("import requests")
import requests
print("import torf")
from torf import Torrent


# config
rqbit_url = "http://localhost:3030"
rqbit_url = "http://localhost:3034"

new_magnets_path = "~/new-magnets.txt"

# https://github.com/milahu/deutschetorrents/blob/main/trackerlist.txt
trackerlist = """
udp://45.9.60.30:6969/announce
udp://142.132.183.104:6969/announce
udp://185.216.179.62:25/announce
udp://93.158.213.92:1337/announce
udp://5.255.124.190:6969/announce
"""


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

def main():

    magnet_link_list = []

    # show rqbit info
    # todo catch requests.exceptions.ConnectionError
    if 0:
        print("server version...")
        d = requests.get(f"{rqbit_url}/").json()
        print(d["server"], d["version"])
        #sys.exit()

    for content_path in sys.argv[1:]:

        print("-"*80)

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
        if content_path.startswith("cas/btih/"):
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
                with open("new-torrents.txt", "a") as f:
                    f.write(str(t.magnet()) + "\n")
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

        p = ".cache/rqbit/" + btih.lower() + ".torrent"
        if os.path.exists(p):
# todo check if rqbit has this torrent
            print("info: torrent exists", p)
            continue

        if not os.path.exists(torrent_file_path):
            t.write(torrent_file_path)

        #print("btmh", repr(btmh))
        btmh = None # FIXME

        #torrent_name = torrenttools("show", "name", torrent_file_path)
        torrent_name = t.name

        src_content_path = content_path

        # prefer btih for hybrid torrents
        # because most tools dont support v2 torrents
        if btih:
            content_path = os.environ["HOME"] + "/cas/btih/" + btih + "/" + torrent_name
        elif btmh:
            content_path = os.environ["HOME"] + "/cas/btmh/" + btmh + "/" + torrent_name
        else:
            print("error: failed to get hash of torrent:", torrent_file_path)
            sys.exit(1)

        os.makedirs(os.path.dirname(content_path), exist_ok=True)
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
            print(f"mv {src_content_path!r} {content_path!r}")
            shutil.move(src_content_path, content_path)

        src_torrent_file_path = torrent_file_path
        torrent_file_path = content_path + ".torrent"

        print(f"mv {src_torrent_file_path!r} {torrent_file_path!r}")
        shutil.move(src_torrent_file_path, torrent_file_path)

        print("torrent", btih, torrent_name)

        print("content_path", content_path)

        #content_dir_path = os.path.dirname(content_path)
        #print("content_dir_path", content_dir_path)

        print("magnet", magnet_link)

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
        # we send torrent file so
        # this should be non-blocking
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

    print()

    for m in magnet_link_list:
        print(m)



if __name__ == "__main__":

    main()
