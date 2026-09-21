#!/usr/bin/env python3

# FIXME this should pause low-progress seeds more aggressively
# quickfix: reduce MAX_ACTIVE_SEEDS

import os
import sys
import time
import logging
from collections import defaultdict
import json

import qbittorrentapi

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

# example config:
"""
{
  "host": "127.0.0.1",
  "port": 9001,
  "username": "admin",
  "password": "xxx"
}
"""
qbt_config_path = os.path.expanduser("~/.config/qbittorrentapi.json")
with open(qbt_config_path) as f:
    conn_info = json.load(f)

CHECK_INTERVAL = 60  # seconds
# CHECK_INTERVAL = 10  # seconds

# If a torrent has peers above this progress, it becomes high priority.
# HIGH_PROGRESS_THRESHOLD = 0.90
HIGH_PROGRESS_THRESHOLD = 0.8

# If a torrent only has peers below this progress, it becomes low priority.
# LOW_PROGRESS_THRESHOLD = 0.10
LOW_PROGRESS_THRESHOLD = 0.4

# Maximum number of seeding torrents we allow simultaneously.
MAX_ACTIVE_SEEDS = 10
MAX_ACTIVE_SEEDS = 5

# Resume paused torrents after this many seconds.
RESUME_AFTER = 300

TODO_TAG = "todo-seed"

# -----------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

paused_by_script = {}


def connect():
    client = qbittorrentapi.Client(**conn_info)
    client.auth_log_in()
    return client


def peer_statistics(client, torrent_hash):
    """
    Returns:
        highest_peer_progress
        lowest_peer_progress
        peer_count
    """

    try:
        peers = client.sync_torrent_peers(torrent_hash).peers
    except Exception:
        return None

    if not peers:
        return None

    progresses = []

    for peer in peers.values():
        progress = getattr(peer, "progress", None)
        if progress is None: continue
        # NOTE peers with progress=0 are not actual leechers
        if progress == 0: continue
        progresses.append(progress)

    if not progresses:
        return None

    return {
        "max": max(progresses),
        "min": min(progresses),
        "count": len(progresses),
    }


def resume_expired(client):
    now = time.time()

    expired = [
        torrent_hash
        for torrent_hash, ts in paused_by_script.items()
        if now - ts >= RESUME_AFTER
    ]

    for torrent_hash in expired:
        try:
            torrent = client.torrents_info(torrent_hashes=torrent_hash)[0]

            logging.info(
                "Resuming previously paused torrent: %s",
                torrent.name,
            )

            torrent.resume()

            tags = [t.strip() for t in torrent.tags.split(",") if t.strip()]
            tags = [t for t in tags if t != TODO_TAG]

            torrent.remove_tags()
            if tags:
                torrent.add_tags(tags)

        except Exception as exc:
            logging.warning("Resume failed: %s", exc)

        paused_by_script.pop(torrent_hash, None)


def classify_torrents(client):
    high_priority = []
    low_priority = []
    normal = []

    torrents = client.torrents_info(status_filter="seeding")

    for torrent in torrents:

        stats = peer_statistics(client, torrent.hash)

        if not stats:
            continue

        max_progress = stats["max"]

        if max_progress >= HIGH_PROGRESS_THRESHOLD:
            high_priority.append((torrent, stats))

        # NOTE peers with progress=0 are not actual leechers
        elif 0 < max_progress <= LOW_PROGRESS_THRESHOLD:
            low_priority.append((torrent, stats))

        else:
            normal.append((torrent, stats))

    return high_priority, normal, low_priority


def scheduler(client):
    high_priority, normal, low_priority = classify_torrents(client)

    active_count = (
        len(high_priority)
        + len(normal)
        + len(low_priority)
    )

    logging.info(
        "High=%d Normal=%d Low=%d Active=%d",
        len(high_priority),
        len(normal),
        len(low_priority),
        active_count,
    )

    if active_count <= MAX_ACTIVE_SEEDS:
        return

    excess = active_count - MAX_ACTIVE_SEEDS

    low_priority.sort(
        key=lambda item: item[1]["max"]
    )

    for torrent, stats in low_priority[:excess]:

        if torrent.hash in paused_by_script:
            continue

        logging.info(
            "Pausing %s (best peer progress %.1f%%)",
            torrent.name,
            stats["max"] * 100,
        )

        try:
            torrent.pause()
            torrent.add_tags(TODO_TAG)

            paused_by_script[torrent.hash] = time.time()

        except Exception as exc:
            logging.warning(
                "Failed to pause %s: %s",
                torrent.name,
                exc,
            )


def main():
    client = connect()

    logging.info("Connected to qBittorrent")

    while True:
        try:
            resume_expired(client)
            scheduler(client)

        except Exception:
            logging.exception("Scheduler iteration failed")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
