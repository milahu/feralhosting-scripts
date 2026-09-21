#!/usr/bin/env python3

# copy all torrent files to cas/btih/{btih}.torrent

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
import json
import re
import argparse
from typing import List

import qbittorrentapi
import torf

# config
# not used
'''
cas_config_path = os.path.expanduser("~/.config/cas.json")
# example config:
"""
{
  "dirs": [
    "/run/media/user/WSC14YZM_8TB/cas"
  ]
}
"""
'''

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



###################



# not used
'''
with open(cas_config_path) as f:
    cas_config = json.load(f)
cas_path_list = cas_config["dirs"]
'''

with open(qbt_config_path) as f:
    conn_info = json.load(f)


def main():
    with qbittorrentapi.Client(**conn_info) as qbt_client:
        return main_inner(qbt_client)


def main_inner(qbt_client):

    # Argument parser
    parser = argparse.ArgumentParser(
        description="Export qBittorrent torrent files to a CAS filesystem."
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        required=False,
        # default="./cas",
        help=(
            'Write output files to "{path}/{hashtype}/{hash}.torrent". '
            'Hashtype is "btih" for v1/hybrid torrents, or "btmh" for v2 torrents.'
        ),
    )
    parser.add_argument(
        "--tags",
        type=str,
        required=False,
        help=(
            "Filter torrents by tag expression. "
            "Examples: 'tag-a && tag-b', 'tag-a || tag-b', '(tag-a && tag-b) || tag-c'"
        ),
    )
    parser.add_argument(
        "--status-seeding", # args.status_seeding
        action="store_true",
        help=(
            "Only process torrents with status = seeding"
        ),
    )
    parser.add_argument(
        "--no-private-torrents", # args.no_private_torrents
        action="store_true",
        help=(
            "Dont process private torrents"
        ),
    )
    parser.add_argument(
        "--remove-extra-files", # args.remove_extra_files
        action="store_true",
        help=(
            "Remove extra torrent files from the output directory"
        ),
    )
    args = parser.parse_args()

    output_dir = os.path.abspath(args.output_dir) if args.output_dir else None
    tag_expr = args.tags
    tag_filter = parse_tag_expr(tag_expr) if tag_expr else None

    if args.remove_extra_files and not output_dir:
        print("error: remove-extra-files requires output-dir")
        sys.exit(1)

    if output_dir:
        print(f"Output directory: {output_dir}")
    if tag_expr:
        print(f"Tag filter expression: {tag_expr}")
    if args.status_seeding:
        print(f"Status filter: seeding")

    # display qBittorrent info
    if 1:
        print(f"qBittorrent: {qbt_client.app.version}")
        print(f"qBittorrent Web API: {qbt_client.app.web_api_version}")
        #for k, v in qbt_client.app.build_info.items():
        #    print(f"{k}: {v}")

    if args.remove_extra_files:
        seen_btih_set = set()
        seen_btmh_set = set()

    for torrent in qbt_client.torrents_info():

        # time.sleep(1) # debug

        # FIXME torrent.info.hash is a truncated btmh hash (v2 infohash)
        # for hybrid or v2-only torrents
        # https://github.com/rmartin16/qbittorrent-api/issues/237
        # https://github.com/qbittorrent/qBittorrent/issues/18185
        torrent_id = torrent.hash

        debug_torrent_id = None
        # debug_torrent_id = "xxx"

        if debug_torrent_id and torrent_id != debug_torrent_id:
            continue

        # filter by status
        if args.status_seeding:
            if not torrent.state_enum.is_uploading:
                if not torrent.state in ["metaDL", "stoppedDL", "stoppedUP", "missingFiles", "stalledDL", ]:
                    print(f"not seeding: {torrent.name} -- state: {torrent.state}")
                    time.sleep(1)
                continue

        # filter by private
        if args.no_private_torrents:
            if torrent.private:
                # print(f"ignoring private torrent: {torrent.name}")
                continue

        # filter by tags
        if tag_filter:
            tags = set(torrent.tags.split(", ") or [])
            if not tag_filter(tags):
                # print(f"wrong tags: {torrent.tags!r} @ {torrent.name}")
                continue

        btih = torrent.infohash_v1
        btmh = torrent.infohash_v2
        if len(btih) != 40:
            # FIXME handle v2-only torrents
            print(f"non-v1 btih: {btih}")
            continue

        # FIXME get the original torrent name
        # WONTFIX this requires qBittorrent 5.1.1 (but i have 5.1.0)
        if 0:
            # https://github.com/qbittorrent/qBittorrent/pull/21015
            # GET /api/v2/torrents/fetchMetadata?source=$source
            # source: magnet URI, torrent infohash (torrent ID?), torrent URL
            # https://github.com/rmartin16/qbittorrent-api/blob/09a09f1c6632baf383b3fb0e227e9c3d0f9d6e43/src/qbittorrentapi/request.py#L572
            # TODO how to call "hidden" API methods
            # "hidden" as in: not-yet exposed by qbittorrentapi
            res = qbt_client._auth_request(
                http_method="post",
                api_namespace="torrents",
                api_method="fetchMetadata",
                # requests_args=requests_args,
                # requests_params=requests_params,
                # headers=headers,
                params=dict(source=torrent_id),
                # data=data,
                # files=files,
                # response_class=response_class,
                # version_introduced=version_introduced,
                # version_removed=version_removed,
                # **kwargs,
            )
            print("res", res)

        # NOTE this can be different that the original name
        name = torrent.name
        # print("name", name)

        content_path = torrent.content_path

        if torrent.content_path == "":
            print("no content: ")
            if torrent.infohash_v1:
                print(f"  torrent.infohash_v1:  {torrent.infohash_v1}")
            if torrent.infohash_v2:
                print(f"  torrent.infohash_v2:  {torrent.infohash_v2}")
            continue

        if 0:
            for key in torrent:
                print(key, torrent[key])
            break

        if 0:
            # TODO also implement this for remote qbittorrent instances
            # api/v2/torrents/export?hash={torrent_id}
            # https://qbittorrent-api.readthedocs.io/en/latest/apidoc/torrents.html#qbittorrentapi.torrents.TorrentsAPIMixIn.torrents_export

            # get the original name from the .torrent file
            torrent_file_path = os.path.expanduser(f"~/.local/share/qBittorrent/BT_backup/{torrent_id}.torrent")
            # FIXME torf does not support v2 torrents https://github.com/rndusr/torf/issues/55
            if not os.path.exists(torrent_file_path):
                print(f"missing torrent file {torrent_file_path}")
                # torrent status: fetching metadata
                continue

            torf_torrent = torf.Torrent.read(torrent_file_path)
            print("original name", torf_torrent.name)
            name = torf_torrent.name
            break # debug

        btih = torrent.infohash_v1
        btmh = torrent.infohash_v2

        if btih:
            # prefer btih for hybrid torrents
            cas_subdir_parts = ["btih", btih]
        elif btmh:
            cas_subdir_parts = ["btmh", btmh]
        else:
            print(f"FIXME failed to parse infohash: torrent_id={torrent_id} btih={btih} btmh={btmh}")
            continue

        if os.path.dirname(content_path) != torrent.save_path:
            # "single file in direcotry" torrent
            # content_path should be the directory path, not the file path
            content_path = os.path.dirname(content_path)
            if 0:
                # debug
                print(f"fixing content_path:")
                print(f"  torrent.content_path: {torrent.content_path!r}")
                print(f"  content_path:         {content_path!r}")

        if os.path.dirname(content_path) != torrent.save_path:
            print(f"bad content_path:")
            if torrent.infohash_v1:
                print(f"  torrent.infohash_v1:  {torrent.infohash_v1}")
            if torrent.infohash_v2:
                print(f"  torrent.infohash_v2:  {torrent.infohash_v2}")
            print(f"  torrent.content_path: {torrent.content_path!r}")
            print(f"  torrent.save_path:    {torrent.save_path!r}")
            continue

        content_path_parts = content_path.split("/")

        if not (content_path_parts[-4] == "cas" and content_path_parts[-3] in ["btih", "btmh"]):
            print(f"not in cas: {content_path!r}")
            continue

        # content is stored in a CAS filesystem
        # content_path = f"{cas_parent_dir}/cas/btih/{btih}/{name}"

        if args.remove_extra_files:
            if btih: seen_btih_set.add(btih)
            if btmh: seen_btmh_set.add(btmh)

        if output_dir:
            path = "/".join([output_dir] + cas_subdir_parts) + ".torrent"
            # print(f"path: {path}")
        else:
            #path = cas_path + f"/btih/{btih}/{name}.torrent"
            # path is compatible with the "cas" parameter at
            # https://github.com/bittorrent/bittorrent.org/pull/171
            #path = cas_path + f"/btih/{btih}.torrent"
            path = torrent.save_path + ".torrent"

        if os.path.exists(path):
            continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            _bytes = torrent.export()
        except Exception as exc:
            print(f"failed to export torrent {btih} {torrent.name}: {exc}")
            continue
        print(f"writing {path}")
        with open(path, "wb") as f:
            f.write(_bytes)

    if args.remove_extra_files:
        dir_path = output_dir + "/btih"
        if os.path.exists(dir_path):
            for file_name in sorted(os.listdir(dir_path)):
                btih = file_name[0:40]
                if btih in seen_btih_set: continue
                file_path = dir_path + "/" + file_name
                print(f"removing extra torrent file: {file_path}")
                os.unlink(file_path)
        dir_path = output_dir + "/btmh"
        if os.path.exists(dir_path):
            for file_name in sorted(os.listdir(dir_path)):
                btmh = file_name[0:64]
                if btmh in seen_btmh_set: continue
                file_path = dir_path + "/" + file_name
                print(f"removing extra torrent file: {file_path}")
                os.unlink(file_path)


def parse_tag_expr(expr: str):
    """
    Parse a boolean tag expression and return a callable that evaluates
    it given a set of tags.

    Supported syntax:
      - tag identifiers: [A-Za-z0-9_-]+
      - parentheses: (expr)
      - operators:
          !   NOT
          &&  AND
          ||  OR
    Example:
        (tag-a && !tag-b) || tag-c
    """

    token_re = re.compile(r"\s*(\!|\(|\)|&&|\|\||[A-Za-z0-9_-]+)\s*")
    tokens = token_re.findall(expr)
    pos = 0

    def peek():
        return tokens[pos] if pos < len(tokens) else None

    def consume(expected=None):
        nonlocal pos
        tok = peek()
        if expected and tok != expected:
            raise ValueError(f"Expected {expected}, got {tok}")
        pos += 1
        return tok

    # Grammar with precedence:
    # expr   := or_expr
    # or_expr := and_expr ( "||" and_expr )*
    # and_expr := not_expr ( "&&" not_expr )*
    # not_expr := "!" not_expr | primary
    # primary := TAG | "(" expr ")"

    def parse_expr():
        return parse_or()

    def parse_or():
        node = parse_and()
        while peek() == "||":
            consume("||")
            rhs = parse_and()
            node = ("or", node, rhs)
        return node

    def parse_and():
        node = parse_not()
        while peek() == "&&":
            consume("&&")
            rhs = parse_not()
            node = ("and", node, rhs)
        return node

    def parse_not():
        if peek() == "!":
            consume("!")
            operand = parse_not()
            return ("not", operand)
        return parse_primary()

    def parse_primary():
        tok = peek()
        if tok is None:
            raise ValueError("Unexpected end of expression")
        if tok == "(":
            consume("(")
            node = parse_expr()
            consume(")")
            return node
        elif re.match(r"[A-Za-z0-9_-]+", tok):
            consume()
            return ("tag", tok)
        else:
            raise ValueError(f"Unexpected token: {tok}")

    ast = parse_expr()
    if pos != len(tokens):
        raise ValueError(f"Unexpected tokens at end: {tokens[pos:]}")

    def eval_ast(node, tags: set):
        kind = node[0]
        if kind == "tag":
            return node[1] in tags
        elif kind == "and":
            return eval_ast(node[1], tags) and eval_ast(node[2], tags)
        elif kind == "or":
            return eval_ast(node[1], tags) or eval_ast(node[2], tags)
        elif kind == "not":
            return not eval_ast(node[1], tags)
        else:
            raise ValueError(f"Invalid AST node: {node}")

    return lambda tags: eval_ast(ast, tags)


def test_parse_tag_expr():
    """
    Basic test suite for parse_tag_expr()
    Run this manually for quick validation.
    """

    tests = [
        # (expression, tags, expected_result)
        ("(a&&b)||c", {"d"}, False),
        ("(a&&b)||c", {"a", "b"}, True),
        ("(a&&b)||c", {"c"}, True),
        ("a&&b||c", {"a"}, False),          # same as ((a && b) || c)
        ("a&&b||c", {"a", "b"}, True),
        ("a&&b||c", {"c"}, True),
        ("a&&b||c", {"a", "c"}, True),
        ("a&&(b||c)", {"a", "b"}, True),
        ("a&&(b||c)", {"a", "c"}, True),
        ("a&&(b||c)", {"a"}, False),
        ("a&&(b||c)", {"b"}, False),
        ("a&&(b||c)", {"a", "d"}, False),
        # True or False and False == True
        ("x||y&&z", {"x"}, True),           # precedence: && > ||
        ("x||y&&z", {"y", "z"}, True),
        # False or True and False == False
        ("x||y&&z", {"y"}, False),
        ("x||y&&z", {"z"}, False),
        # (True or False) and False == False
        ("(x||y)&&z", {"x"}, False),
        ("(x||y)&&z", {"x", "z"}, True),
        ("(x||y)&&z", {"y", "z"}, True),
        ("(x||y)&&z", {"y"}, False),
        # negation
        ("!a", {"a"}, False),
        ("!a", {"b"}, True),
        ("a && !b", {"a"}, True),
        ("a && !b", {"a", "b"}, False),
        ("a && !(b || c)", {"a"}, True),
        ("a && !(b || c)", {"a", "b"}, False),
        ("a && !(b || c)", {"a", "c"}, False),
        ("!(a && b)", {"a"}, True),
        ("!(a && b)", {"a", "b"}, False),
        ("!!a", {"a"}, True),
    ]

    passed = 0
    failed = 0

    for expr, tags, expected in tests:
        try:
            func = parse_tag_expr(expr)
            result = func(tags)
            if result == expected:
                print(f"✅ {expr!r} with {tags} => {result}")
                passed += 1
            else:
                print(f"❌ {expr!r} with {tags} => {result} (expected {expected})")
                failed += 1
        except Exception as e:
            print(f"💥 {expr!r} raised {e}")
            failed += 1

    print(f"\nSummary: {passed} passed, {failed} failed, total {passed + failed}")


if 0:
    test_parse_tag_expr(); sys.exit()


if __name__ == "__main__":

    main()
