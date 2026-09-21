#!/usr/bin/env python3

# create "reseed" torrents from "reseed-todo" torrents
# also slightly modify the torrent contents:
# remove trash files, rename files (spaces to dots)

# TODO produce streamable MP4 files
# check if a MP4 file is streamable:
# https://superuser.com/questions/1753260/what-makes-a-mp4-streamable
# fast: AtomicParsley "$i" -T | grep "Atom moov"
# slow: ffmpeg -v trace -i "$i" /dev/null 2>&1 | grep -m1 -o "type:'moov'"
# make a MP4 file streamable:
# ffmpeg -i src.mp4 -map 0 -c copy -movflags faststart dst.mp4

# FIXME retry requests
# TimeoutError
# urllib3.exceptions.ReadTimeoutError
# requests.exceptions.ReadTimeout
# qbittorrentapi.exceptions.APIConnectionError

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
import shlex
import subprocess
import glob
import tempfile


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

reseed_torrents_btih_list = [
    # "c0b61da2190de7108b7a59e40af915f45da0b747",
]

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
# src_config_path = os.path.expanduser("~/.config/qbittorrentapi-private.json")
src_config_path = os.path.expanduser("~/.config/qbittorrentapi-no-vpn.json")
dst_config_path = os.path.expanduser("~/.config/qbittorrentapi.json")

# https://github.com/milahu/deutschetorrents/blob/main/trackerlist.txt
# udp://142.132.183.104:6969/announce # not working
# udp://5.255.124.190:6969/announce # no peers
trackerlist = """
udp://45.9.60.30:6969/announce
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



with open(cas_config_path) as f:
    cas_config = json.load(f)
cas_path_list = cas_config["dirs"]

with open(src_config_path) as f:
    src_conn_info = json.load(f)

with open(dst_config_path) as f:
    dst_conn_info = json.load(f)

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


# video file extensions
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".webm"}



# mp4-is-streamable.py

# Check if an MP4 file is streamable (faststart enabled).
# A file is streamable if the 'moov' atom appears before 'mdat'.

# https://superuser.com/questions/559372/using-ffmpeg-to-locate-moov-atom

import os
import re
import sys
import subprocess

MAX_HEADER_SIZE = 5 * 1024 * 1024  # 5 MiB
MAX_LINES = 10_000  # only read first 10K lines of ffmpeg output

def check_mp4_is_streamable(filename, max_lines=MAX_LINES, max_header_size=MAX_HEADER_SIZE):
    """
    Returns True if the MP4 file is streamable (moov before mdat), False otherwise.
    """
    proc = subprocess.Popen(
        ["ffmpeg", "-hide_banner", "-v", "trace", "-i", filename],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env={
            "PATH": os.environ["PATH"],
            "LANG": "C",
        }
    )

    moov_offset = None
    mdat_offset = None

    moov_re = re.compile(rb"type:'moov'.*sz:\s*([0-9]+)\s*([0-9]+)\s*([0-9]+)")
    mdat_re = re.compile(rb"type:'mdat'.*sz:\s*([0-9]+)\s*([0-9]+)\s*([0-9]+)")

    for i, line in enumerate(proc.stdout):
        if i >= max_lines:
            break

        if moov_offset is None:
            if m := moov_re.search(line):
                moov_offset = int(m.group(2))  # start offset of moov atom

        if mdat_offset is None:
            if m := mdat_re.search(line):
                mdat_offset = int(m.group(2))  # start offset of mdat atom

        if moov_offset is not None and mdat_offset is not None:
            break

    proc.terminate()
    try:
        proc.wait(timeout=1)
    except subprocess.TimeoutExpired:
        proc.kill()

    if moov_offset is None:
        is_streamable = False  # no moov atom found
    elif mdat_offset is None:
        # is_streamable = False  # no mdat atom found
        is_streamable = moov_offset <= max_header_size
    else:
        # streamable if moov appears before mdat and is within header size
        is_streamable = moov_offset < mdat_offset and moov_offset <= max_header_size

    if 0:
        # debug
        if not is_streamable:
            print(f"{filename}: moov_offset={moov_offset} mdat_offset={mdat_offset}", file=sys.stderr)

    return is_streamable


def check_video_is_streamable(filepath: str) -> bool:
    """
    Check if a video file is streamable by using ffprobe.
    For MP4: we check if 'movflags faststart' was applied (moov atom at beginning).
    For MKV and others: we check if ffprobe reports 'isom' or other hints.
    """
    if filepath[-4:].lower() == ".mp4":
        return check_mp4_is_streamable(filepath)
    # TODO check other file types
    # assume that all MKV files are streamable
    # https://stackoverflow.com/questions/79768192/check-if-an-mkv-file-is-streamable
    return True
    try:
        # Run ffprobe to check file info
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=filename,format_name", "-print_format", "json", filepath],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        info = result.stdout.lower()
        # A very rough heuristic: mp4 needs faststart, mkv sometimes too
        if filepath.lower().endswith(".mp4"):
            # Check for "faststart" marker using qt-faststart heuristic
            probe = subprocess.run(
                ["ffprobe", "-v", "trace", filepath],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            # If moov atom appears after mdat, it's not streamable
            return '"moov"' in probe.stdout.split("mdat")[0]
        elif filepath.lower().endswith(".mkv"):
            # MKV should usually be streamable, but sometimes it's not
            # Use ffprobe's "start_time" field: if it's "N/A", it's not seekable/streamable
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=start_time", "-of", "default=nw=1:nk=1", filepath],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            start_time = result.stdout.strip()
            return start_time != "N/A"
        else:
            # For other formats, assume not streamable (safe choice)
            return False
    except Exception as e:
        print(f"Error probing {filepath}: {e}")
        return False


def make_streamable_video(filepath: str):
    """Re-encode container to make video streamable, in-place."""
    ext = os.path.splitext(filepath)[1].lower()
    temp_path = filepath + ".tmp" + ext # use the same filesystem, not /tmp

    try:
        cmd = ["ffmpeg", "-hide_banner", "-i", filepath] # input
        cmd += ["-c", "copy", "-map", "0", "-map_metadata", "0"] # copy
        cmd += ["-movflags", "faststart"] # make streamable
        if ext != ".mp4":
            cmd += ["-fflags", "+genpts"] # make streamable
        cmd += [temp_path] # output

        print("Running:", " ".join(cmd))
        subprocess.run(cmd, check=True)

        # Replace original with processed
        shutil.move(temp_path, filepath)
        print(f"Made streamable: {filepath}")
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg failed on {filepath}: {e}")
        if os.path.exists(temp_path):
            os.remove(temp_path)


def make_streamable_video(filepath: str):
    """Make video streamable, in-place."""
    ext = os.path.splitext(filepath)[1].lower()
    # temp_fd, temp_path = tempfile.mkstemp(suffix=ext)
    # os.close(temp_fd)
    # FIXME limit filename length to 256 bytes
    temp_path = f"{filepath}.temp-{time.time()}{ext}"

    try:
        if ext in {".mp4", ".mov"}:
            cmd = ["ffmpeg", "-i", filepath, "-c", "copy", "-movflags", "faststart", temp_path]
        elif ext in {".mkv", ".webm"}:
            # https://superuser.com/questions/1190153/make-mkv-file-suitable-for-streaming-with-ffmpeg-or-avconv-how-to-move-all-m
            cmd = ["mkclean", "--no-optimize", filepath, temp_path]
        else:
            cmd = ["ffmpeg", "-i", filepath, "-c", "copy", "-movflags", "faststart", temp_path]

        print("Running:", " ".join(cmd))
        subprocess.run(cmd, check=True)

        shutil.move(temp_path, filepath)
        print(f"Made streamable: {filepath}")
    except subprocess.CalledProcessError as e:
        print(f"Conversion failed on {filepath}: {e}")
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise Exception(f"make_streamable_video failed on {filepath!r}")


def make_streamable_directory(root_dir: str):
    for dirpath, _, filenames in os.walk(root_dir):
        for fname in filenames:
            ext = os.path.splitext(fname)[1].lower()
            if ext in VIDEO_EXTENSIONS:
                filepath = os.path.join(dirpath, fname)
                print(f"Checking: {filepath}")
                if not check_video_is_streamable(filepath):
                    print(f"Not streamable, fixing: {filepath}")
                    make_streamable_video(filepath)
                else:
                    print(f"Already streamable: {filepath}")


def main():
    with (
        qbittorrentapi.Client(**src_conn_info) as src_qbt_client,
        qbittorrentapi.Client(**dst_conn_info) as dst_qbt_client,
    ):
        return main_inner(src_qbt_client, dst_qbt_client)

def main_inner(src_qbt_client, dst_qbt_client):

    magnet_link_list = []

    if 1:
        print(f"src qBittorrent: {src_qbt_client.app.version}")
        print(f"dst qBittorrent: {dst_qbt_client.app.version}")
        print(f"src qBittorrent Web API: {src_qbt_client.app.web_api_version}")
        print(f"dst qBittorrent Web API: {dst_qbt_client.app.web_api_version}")
        #for k, v in src_qbt_client.app.build_info.items():
        #    print(f"{k}: {v}")

    # wait for checking torrents
    while True:
        checking = False
        for torrent in src_qbt_client.torrents_info("checking"):
            checking = True
            print(f"waiting for checking torrent {torrent.info.hash} {torrent.name}")
            time.sleep(10)
        if not checking: break

    reseed_torrents = dict()
    for torrent in src_qbt_client.torrents_info("completed"):
        # if not "reseed" in torrent.tags: # no! torrent.tags is a string like "tag1, tag2"
        if not ", reseed," in (", " + torrent.tags + ","):
            continue
        if not torrent.name in reseed_torrents:
            reseed_torrents[torrent.name] = []
        reseed_torrents[torrent.name].append(torrent.info.hash)

    for torrent in src_qbt_client.torrents_info("completed"):

        # if torrent.info.hash != "64217d036bb48b9b98c19f26a2fdc0b17e81e30e": continue

        if reseed_torrents_btih_list:
            try:
                btih = torrent.info.hash
            except AttributeError:
                # 'TorrentDictionary' instance has no attribute 'hash'
                continue
            if not btih in reseed_torrents_btih_list:
                continue
        else:
            # if not "reseed-todo" in torrent.tags: # no! torrent.tags is a string like "tag1, tag2"
            if not ", reseed-todo," in (", " + torrent.tags + ","):
                continue

        # torrent.save_path /run/media/user/ZCT01TB4_8tb/cas/todo
        # TODO use cas_path_list
        # if torrent.save_path != "/run/media/user/ZCT01TB4_8tb/cas/todo":
        # if torrent.save_path != "/media/ZCT01TB4_8tb/cas/todo":
        # if torrent.save_path != "/media/ZYD82805_24TB/cas/todo":
        if 0:
            print("ignoring torrent with save_path", torrent.save_path)
            continue

        # check if this torrent already has a "reseed" torrent
        if torrent.name in reseed_torrents:
            print(f"torrent {torrent.info.hash} {torrent.name} already has a reseed torrent: {reseed_torrents[torrent.name]}")
            torrent.add_tags("reseed-done")
            torrent.remove_tags("reseed-todo")
            continue

        print("torrent save_path", torrent.save_path)

        content_path = torrent.save_path + "/" + torrent.name
        print("torrent content_path", torrent.save_path)

        content_path = os.path.normpath(content_path)
        print("torrent content_path", torrent.save_path)

        # create a new torrent



        if not os.path.exists(content_path):
            print(f"error: missing content_path {content_path!r}")
            continue

        """
        new_magnet_path = content_path + ".new-magnet.txt"
        if os.path.exists(new_magnet_path):
            # fixme can be missing in rqbit
            # todo check if rqbit has this torrent
            print("has new torrent")
            continue
        """

        if content_path.lower().endswith(".torrent"):
            print("skipping .torrent file")
            continue

        if content_path.lower().endswith(".new-magnet.txt"):
            print("skipping .new-magnet.txt file")
            continue



        # copy to temp path

        # rename the main directory or file
        # FIXME move this to "rename content files"
        src_content_path = content_path
        temp_dir = os.path.dirname(src_content_path) + f"/temp-{time.time()}"
        os.makedirs(temp_dir, exist_ok=False) # should not exist before
        content_basename = os.path.basename(src_content_path)
        content_basename = content_basename.replace(" ", ".") # spaces to dots
        content_basename = re.sub(r"\.\.+", ".", content_basename) # collapse dots
        content_path = temp_dir + "/" + content_basename

        if os.path.isdir(src_content_path):
            # https://stackoverflow.com/questions/10778229/recursively-creating-hardlinks-using-python
            print(f"cp -rl {src_content_path!r} {content_path!r}")
            shutil.copytree(src_content_path, content_path, copy_function=os.link)
        else:
            # os.path.isfile(src_content_path) == True
            print(f"moving file to directory: {src_content_path!r}")
            content_path = os.path.splitext(content_path)[0]
            print(f"mkdir {content_path!r}")
            os.mkdir(content_path)
            content_path_file = content_path + "/" + os.path.basename(src_content_path)
            print(f"ln {src_content_path!r} {content_path_file!r}")
            os.link(src_content_path, content_path_file)

        # use relative paths, which are shorter than absolute paths
        os.chdir(content_path)

        # no, this is too invasive in general
        # this should be done only on few torrents
        """
        # rename content files
        for path, dirs, files in os.walk(content_path):
            for file in (files + dirs):
                file2 = file[:]
                file2 = file2.replace(" ", ".") # spaces to dots
                file2 = re.sub(r"\.\.+", ".", file2) # collapse dots
                if file == file2:
                    continue
                file = os.path.join(path, file)
                file2 = os.path.join(path, file2)
                print(f"mv {file!r} {file2!r}")
                os.rename(file, file2)
        """

        extraction_failed = False
        for rar_path in glob.glob("./**/*.rar", recursive=True):
            args = [
                "unrar",
                "x", # extract
                "-o+", # overwrite existing files
                os.path.basename(rar_path),
            ]
            workdir = os.path.dirname(rar_path)
            print(f"( cd {workdir!r} && {shlex.join(args)} )")
            # FIXME handle subprocess.CalledProcessError
            # Command '['unrar', 'x', 'watchable-thewailing-1080-de.rar']' returned non-zero exit status 3.
            # expected:
            #   remove tempfiles
            #   remove label reseed-todo
            #   add label reseed-failed-extract
            # output:
            # Extracting from watchable-thewailing-1080-de.rar
            # Extracting from watchable-thewailing-1080-de.r00
            # Extracting from watchable-thewailing-1080-de.r01
            # watchable-thewailing-1080-de.mkv - checksum error
            # Unexpected end of archive
            # Total errors: 18
            try:
                subprocess.check_call(args, cwd=workdir)
            except subprocess.CalledProcessError as exc:
                print(f"failed to extract archives in torrent {torrent.hash} {torrent.name}: {exc}")
                extraction_failed = True
                break # stop extracting files
            rar_path_base = os.path.splitext(rar_path)[0]
            for file_path in glob.glob(rar_path_base + ".*"):
                if not re.search(r"\.(rar|sfv|r[0-9]+)$", file_path):
                    continue
                print(f"rm {file_path!r}")
                os.unlink(file_path)

        if extraction_failed:
            # remove tempfiles
            print(f"rm -r {temp_dir!r}")
            shutil.rmtree(temp_dir)
            torrent.add_tags("reseed-failed-extract")
            torrent.remove_tags("reseed-todo")
            continue # stop processing this torrent

        # modify contents
        # FIXME force-remove read-only files
        trash_regex_list = [
            re.compile(r"proof(|\.[a-z0-9]+)", re.I), # proof.jpg
            re.compile(r"sample(|\.[a-z0-9]+)", re.I), # sample.mkv
            re.compile(r"desktop\.ini", re.I),
            re.compile(r"Icon\.ico", re.I),
            re.compile(r"Thumbs\.db", re.I),
            re.compile(r".*\.sfv", re.I), # checksums
            # re.compile(r".*\.nfo", re.I),
        ]
        for dirpath, dirnames, filenames in os.walk("."):
            for filename in (dirnames + filenames):
                filepath = os.path.join(dirpath, filename)
                for regex in trash_regex_list:
                    if not regex.fullmatch(filename): continue # keep file
                    if os.path.isdir(filepath):
                        print(f"rm -r {filepath!r}")
                        shutil.rmtree(filepath)
                    else:
                        print(f"rm {filepath!r}")
                        os.unlink(filepath)
                    try:
                        # directory was removed -> dont recurse in os.walk
                        dirnames.remove(filepath)
                    except ValueError:
                        pass

        nogo_path_list = [
            # Paris.Paradies.2024.German.DL.1080p.WEB.H264.AUDiOFiX-CLASSiCALHD
            "mkvmerge.exe",
            "audiofix.bat",
        ]

        found_nogo_path = None
        for nogo_path in nogo_path_list:
            if not os.path.exists(nogo_path):
                continue
            torrent.add_tags("nogo-paths")
            found_nogo_path = nogo_path
            break
        if found_nogo_path:
            print(f"error: found nogo path {found_nogo_path!r}")
            print("-"*40)
            continue

        # remove nested nfo files
        for dir_name in os.listdir("."):
            dir_path = dir_name
            if not os.path.isdir(dir_path): continue
            for file_path in glob.glob(f"{dir_path}/**/*.nfo", recursive=True):
                # file_path = dir_path + "/" + file_name
                if not os.path.isfile(file_path): continue # keep .nfo directories
                print(f"rm {file_path!r}")
                os.unlink(file_path)

        # remove single-file directories
        for dir_name in os.listdir("."):
            dir_path = dir_name
            if not os.path.isdir(dir_path): continue
            file_name_list = os.listdir(dir_path)
            if len(file_name_list) != 1: continue
            file_name = file_name_list[0]
            file_path = dir_path + "/" + file_name
            if not os.path.isfile(file_path): continue
            file_ext = file_name.split(".")[-1]
            file_path_new = dir_path + "." + file_ext
            if os.path.exists(file_path_new): continue
            print(f"mv {file_path!r} {file_path_new!r}")
            os.rename(file_path, file_path_new)
            os.rmdir(dir_path)

        # make sure that videos are streamable
        make_streamable_directory(content_path)

        # TODO why re.sub
        torrent_file_path = re.sub(r"[\\/]+$", r"", content_path) + ".torrent"
        print("torrent_file_path", torrent_file_path)

        btih_expected = None

        t = None

        if os.path.exists(torrent_file_path):
            print(f"removing existing torrent file {torrent_file_path!r}")
            os.unlink(torrent_file_path)
            """
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
            """

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
                magnet_link = str(t.magnet())
                p = new_magnets_path
                p = os.path.expanduser(p)
                with open(p, "a") as f:
                    f.write(magnet_link + "\n")
            """
            if not os.path.exists(new_magnet_path):
                with open(new_magnet_path, "w") as f:
                    f.write(str(t.magnet()) + "\n")
            """

        # t.metainfo['more stuff']

        # btih = torrenttools("show", "infohash", "--protocol", "v1", torrent_file_path)
        # btmh = torrenttools("show", "infohash", "--protocol", "v2", torrent_file_path)
        btih = t.infohash
        print("btih", repr(btih))
        assert len(btih) == 40
        # assert len(btmh) == 64

        if dst_qbt_client.torrents_info(hashes=btih):
            print(f"torrent already exists in dst qbittorrent instance")
            # remove tempfiles
            print(f"rm -r {temp_dir!r}")
            shutil.rmtree(temp_dir)
            torrent.add_tags("reseed-failed-dst-exists")
            torrent.remove_tags("reseed-todo")
            continue # stop processing this torrent

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

        """
        if btih_expected and not os.path.exists(new_magnet_path):
            with open(new_magnet_path, "w") as f:
                f.write(str(t.magnet()) + "\n")
        """

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
            try:
                dst_dev = os.stat(path).st_dev
            except FileNotFoundError:
                continue
            if src_dev == dst_dev:
                cas_path = path
                break
        if not cas_path:
            # try to use the same device as src_content_path
            # this assumes that no symlinks are used...
            for p in psutil.disk_partitions():
                # print(p.mountpoint, psutil.disk_usage(p.mountpoint).percent)
                dst_dev = os.stat(p.mountpoint).st_dev
                if src_dev == dst_dev:
                    cas_path = p.mountpoint + "/cas"
                    break
        if not cas_path:
            print(f"error: not found cas_path for src_content_path {src_content_path!r}. src_dev {src_dev} = {format_dev(src_dev)}")
            # TODO print a list of mountpoints
            sys.exit(1)

        # prefer btih for hybrid torrents
        # because most tools dont support v2 torrents
        if btih:
            content_path = cas_path + "/btih/" + btih + "/" + torrent_name
        elif btmh:
            content_path = cas_path + "/btmh/" + btmh + "/" + torrent_name
        else:
            print("error: failed to get hash of torrent:", torrent_file_path)
            sys.exit(1)

        os.makedirs(os.path.dirname(content_path), exist_ok=True)
        # todo more generic check
        #if content_path.startswith("cas/btih/"):
        if True:
            if os.path.exists(content_path):
                """
                print(f"error: content_path exists: {content_path!r}")
                # TODO better
                print("-"*40)
                continue
                #sys.exit(1)
                """
                # TODO remove empty dirs and subdirs
                trash_content_path = f"{content_path}.trash.{time.time()}"
                print(f"mv {content_path!r} {trash_content_path!r}")
                shutil.move(content_path, trash_content_path)
            print(f"mv {src_content_path!r} {content_path!r}")
            shutil.move(src_content_path, content_path)
            """
            # https://stackoverflow.com/questions/10778229/recursively-creating-hardlinks-using-python
            print(f"cp -rl {src_content_path!r} {content_path!r}")
            shutil.copytree(src_content_path, content_path, copy_function=os.link)
            """



        src_torrent_file_path = torrent_file_path
        #torrent_file_path = content_path + ".torrent"
        # torrent_file_path is compatible with the "cas" parameter at
        # https://github.com/bittorrent/bittorrent.org/pull/171
        torrent_file_path = os.path.dirname(content_path) + ".torrent"

        if os.path.exists(torrent_file_path):
            """
            print(f"error: torrent_file_path exists: {torrent_file_path!r}")
            # TODO better
            #sys.exit(1)
            """
            trash_torrent_file_path = f"{torrent_file_path}.trash.{time.time()}"
            print(f"mv {torrent_file_path!r} {trash_torrent_file_path!r}")
            os.rename(torrent_file_path, trash_torrent_file_path)
        if not os.path.exists(torrent_file_path):
            print(f"mv {src_torrent_file_path!r} {torrent_file_path!r}")
            shutil.move(src_torrent_file_path, torrent_file_path)
        else:
            print(f"TODO rm {src_torrent_file_path!r}")

        os.rmdir(temp_dir)

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
        for torrent2 in src_qbt_client.torrents_info():
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
            dst_qbt_client.torrents.add(
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
            for torrent2 in dst_qbt_client.torrents.info():
                try:
                    btih2 = torrent2.info.hash
                except AttributeError:
                    # 'TorrentDictionary' instance has no attribute 'hash'
                    continue
                if btih.lower() == btih2.lower():
                    # torrent2.pause()
                    torrent2.resume()
                    torrent2.add_tags("reseed")
                    torrent2.start() # ?
                    done_start = True
                    break
        print(" ok")



        # wait for checking

        def get_state():
            # TODO better. get state of one torrent
            for torrent2 in dst_qbt_client.torrents_info():
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
            for torrent2 in dst_qbt_client.torrents.info():
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





        torrent.add_tags("reseed-done")
        torrent.remove_tags("reseed-todo")



        print("-"*40)

        # print("sleep 10"); time.sleep(10) # debug

        # break # debug





    print()

    for m in magnet_link_list:
        print(m)



if __name__ == "__main__":

    main()
