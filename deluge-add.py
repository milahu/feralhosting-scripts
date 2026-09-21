#!/usr/bin/env python3

import os
import sys
import json
import base64
import argparse

import torf
import deluge_client
# import deluge_client.client

cas_config_path = os.path.expanduser("~/.config/cas.json")
# example config:
"""
{
  "dirs": [
    "/run/media/user/WSC14YZM_8TB/cas"
  ]
}
"""

# on nixos linux, the deluge config is at /var/lib/deluge/.config/deluge/
# but these files are owned by the deluge user
# TODO add a cli argument "--import-config <path>"
# to import the deluge config from (for example)
# /var/lib/deluge/.config/deluge/auth and
# /var/lib/deluge/.config/deluge/core.conf
# and write the the delugeclient.json config to stdout
CONFIG_JSON = os.path.expanduser("~/.config/delugeclient.json")
DELUGE_DIR = os.path.expanduser("~/.config/deluge")
AUTH_FILE = os.path.join(DELUGE_DIR, "auth")
CORE_CONF = os.path.join(DELUGE_DIR, "core.conf")

with open(cas_config_path) as f:
    cas_config = json.load(f)
cas_path_list = cas_config["dirs"]


def import_deluge_config(import_path: str):
    """
    Import Deluge config from a custom directory and write delugeclient.json to stdout.
    """
    auth_path = os.path.join(import_path, "auth")
    core_conf_path = os.path.join(import_path, "core.conf")

    with open(auth_path) as f:
        auth_lines = f.readlines()

    with open(core_conf_path) as f:
        core_conf = f.read()

    # parse all users in auth file
    users = []
    with open(auth_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(":")
            if len(parts) < 3:
                continue
            username, password, level = parts[0], parts[1], parts[2]
            try:
                level_int = int(level)
            except ValueError:
                continue
            users.append((level_int, username, password))

    if not users:
        print(f"No valid users found in {auth_path}", file=sys.stderr)
        sys.exit(1)

    # pick user with max permission level
    users.sort(reverse=True)  # sort by level descending
    _, username, password = users[0]

    core_data = extract_second_json(core_conf)

    port = core_data.get("daemon_port")
    if not port:
        print(f"No daemon_port found in {core_conf_path}", file=sys.stderr)
        sys.exit(1)

    config_dict = {
        "host": "10.0.0.1", # FIXME detect actual host address
        "port": int(port),
        "username": username,
        "password": password
    }

    print(json.dumps(config_dict, indent=2))
    sys.exit(0)


def print_usage():
    print("Usage: deluge-add.py <torrent1> [<torrent2> ...]")
    print("Adds torrent files to Deluge using settings from ~/.config/delugeclient.json")
    print("If that file does not exist, reads ~/.config/deluge/auth and core.conf instead.")


def load_json_config():
    with open(CONFIG_JSON, "r") as f:
        cfg = json.load(f)
    # NOTE config dict keys must match kwargs of DelugeRPCClient.__init__
    # class DelugeRPCClient(object):
    #     def __init__(self, host, port, username, password, decode_utf8=False, automatic_reconnect=True, timeout=20):
    required = ["host", "port", "username", "password"]
    for key in required:
        if key not in cfg:
            print(f"Missing key '{key}' in {CONFIG_JSON}")
            sys.exit(1)
    return cfg


def extract_second_json(content: str) -> dict:
    """Return the second JSON block in core.conf (everything from 2nd '{' to EOF)."""
    first_end = content.find('}')
    if first_end == -1:
        raise ValueError("No closing brace for first JSON block")
    second_start = content.find('{', first_end + 1)
    if second_start == -1:
        raise ValueError("No second JSON block found")
    second_json_text = content[second_start:].strip()
    try:
        return json.loads(second_json_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse second JSON: {e}")


def load_deluge_native_config():
    user = os.environ.get("USER")
    if not user:
        print("Environment variable USER not set.")
        sys.exit(1)

    if not os.path.exists(AUTH_FILE):
        print(f"Missing Deluge auth file: {AUTH_FILE}")
        sys.exit(1)
    if not os.path.exists(CORE_CONF):
        print(f"Missing Deluge core.conf file: {CORE_CONF}")
        sys.exit(1)

    # read password from auth
    password = None
    with open(AUTH_FILE) as f:
        for line in f:
            if not line.strip() or line.startswith("#"):
                continue
            name, *rest = line.strip().split(":")
            if name == user and len(rest) >= 1:
                password = rest[0]
                break
    if not password:
        print(f"User '{user}' not found in {AUTH_FILE}")
        sys.exit(1)

    with open(CORE_CONF) as f:
        content = f.read()
    core_data = extract_second_json(content)

    port = core_data.get("daemon_port")
    if not port:
        print(f"No daemon_port found in {CORE_CONF}")
        sys.exit(1)

    # NOTE config dict keys must match kwargs of DelugeRPCClient.__init__
    # class DelugeRPCClient(object):
    #     def __init__(self, host, port, username, password, decode_utf8=False, automatic_reconnect=True, timeout=20):
    return {
        "host": "10.0.0.1", # FIXME detect actual host address
        "port": int(port),
        "username": user,
        "password": password
    }


def load_config():
    if os.path.exists(CONFIG_JSON):
        return load_json_config()
    return load_deluge_native_config()


def main():

    parser = argparse.ArgumentParser(description="Add torrents to Deluge")
    parser.add_argument(
        "--import-config",
        metavar="PATH",
        help="Import Deluge config from this directory and output delugeclient.json",
    )
    parser.add_argument(
        "torrents",
        nargs="*",
        metavar="PATH",
        help="Torrent files to add",
    )
    args = parser.parse_args()

    if args.import_config:
        import_deluge_config(args.import_config)

    if not args.torrents:
        print_usage()
        sys.exit(1)

    cfg = load_config()
    try:
        client = deluge_client.DelugeRPCClient(**cfg)
        client.connect()
    except Exception as e:
        print(f"Error connecting to Deluge: {e}")
        sys.exit(1)

    for torrent_path in args.torrents:

        if not os.path.exists(torrent_path):
            print(f"ignoring missing torrent file: {torrent_path}")
            continue

        try:
            torrent = torf.Torrent.read(torrent_path)
        except Exception as exc:
            print(f"ignoring invalid torrent file: {exc}")
            continue

        #content_dir_path = os.path.dirname(content_path)
        content_dir_path = None
        for cas_path in cas_path_list:
            content_dir_path = os.path.join(cas_path, "btih", torrent.infohash)
            if os.path.exists(content_dir_path):
                break
            else:
                content_dir_path = None
        if not content_dir_path:
            print(f"error: no content files for btih={torrent.infohash}")
            continue
        # print("content_dir_path", content_dir_path)

        with open(torrent_path, "rb") as f:
            torrent_data = f.read()
        try:
            # https://deluge-bendikro.readthedocs.io/en/latest/core/rpc.html
            filename = os.path.basename(torrent_path)
            filedump = base64.b64encode(torrent_data).decode('ascii')
            options = {
                "download_location": content_dir_path,
                "add_paused": False,
                # "label": None,
            }
            timeout = 30
            torrent_id = client.core.add_torrent_file(filename, filedump, options)
            if torrent_id is None:
                # torrent exists
                print(f"Keeping torrent {torrent_path}")
            else:
                print(f"Added torrent {torrent_path}: torrent_id={torrent_id}")
        # FIXME AttributeError: module 'deluge_client.client' has no attribute 'AddTorrentError'
        # except deluge_client.client.AddTorrentError as exc:
        except Exception as exc:
            if type(exc).__name__ == "AddTorrentError":
                # deluge_client.client.AddTorrentError
                if exc.args[0].startswith("Torrent already in session"):
                    # torrent exists
                    print(f"Keeping torrent {torrent_path}")
                    continue
            # print(exc, type(exc), type(exc).__name__, exc.args, dir(exc))
            print(f"Failed to add torrent {torrent_path}: {exc}")
            raise

    client.disconnect()


if __name__ == "__main__":
    main()
