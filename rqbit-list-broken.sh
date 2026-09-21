#!/usr/bin/env bash

rqbit_url=http://localhost:3034

# curl http://localhost:3030/torrents  | jq -r '.torrents[] | .id' | sort -n

while read torrent_id torrent_hash; do

  # torrent_id=85

  #if [ -n "$btih" ] && [ "$btih" != "$torrent_hash" ]; then
  if [ -n "$id" ] && [ "$id" != "$torrent_id" ]; then
    continue
  fi

  torrent_data=$(curl -s $rqbit_url/torrents/$torrent_id)

  torrent_name=$(echo "$torrent_data" | jq -r .name)

  # debug broken unicode in title
  # https://github.com/ikatson/rqbit/issues/137
  #if echo "$torrent_name" | grep -E -q "^<[0-9]+ bytes>$"; then
  #  torrent_name+=" btih = $torrent_hash"
  #fi

    # verbose -> slow
    torrent_stats=$(curl -s $rqbit_url/torrents/$torrent_id/stats/v1)

    torrent_finished=$(echo "$torrent_stats" | jq -r .finished)
    if [ "$torrent_finished" = true ]; then
      continue
    fi

    # echo "$torrent_stats" | jq

    # set -eux

    # initializing | live | ...
    torrent_state=$(echo "$torrent_stats" | jq -r .state | head -c4)

    upload_speed=$(echo "$torrent_stats" | jq -r .live.upload_speed.human_readable | tr -d ' ')

    upload_size=$(echo "$torrent_stats" | jq -r .uploaded_bytes | numfmt --to=iec-i --suffix=B)

    download_size=$(echo "$torrent_stats" | jq -r .downloaded_bytes)
    if [ "$download_size" != null ]; then
      download_size=$(echo "$download_size" | numfmt --to=iec-i --suffix=B)
    fi

    torrent_hash_8="${torrent_hash:0:8}"

    printf "%4s %8s %4s %6s %10s %s\n" "$torrent_id" "$torrent_hash_8" "$torrent_state" "$upload_size" "$upload_speed" "$torrent_name"

done < <(
  curl -s $rqbit_url/torrents |
  jq -r '.torrents[] | "\(.id) \(.info_hash)"' | sort -n
)
