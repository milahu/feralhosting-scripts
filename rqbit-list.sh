#!/usr/bin/env bash

rqbit_url=http://localhost:3034

#btih="$1"
id="$1"

# curl http://localhost:3030/torrents  | jq -r '.torrents[] | .id' | sort -n

total_upspeed="0"
#total_upspeed2="0"
total_uptraffic="0"

total_downspeed="0"
total_downtraffic="0"

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

  if true; then

    torrent_stats=$(curl -s $rqbit_url/torrents/$torrent_id/stats)

    # echo "$torrent_stats" | jq

    # exit

    torrent_state=$(echo "$torrent_stats" | jq -r .time_remaining) # null if done

    upload_speed=$(echo "$torrent_stats" | jq -r .upload_speed.human_readable | tr -d ' ')

    upload_size=$(echo "$torrent_stats" | jq -r .snapshot.uploaded_bytes | numfmt --to=iec-i --suffix=B)

    download_speed=$(echo "$torrent_stats" | jq -r .download_speed.human_readable | tr -d ' ')

    download_size=$(echo "$torrent_stats" | jq -r .snapshot.fetched_bytes | numfmt --to=iec-i --suffix=B)

    # speed is in MiB/s
    total_upspeed+=+$(echo "$torrent_stats" | jq -r .upload_speed.mbps)
    #total_upspeed2+=+$(echo "${upload_speed:0: -3}" | numfmt --from=iec-i) # remove "B/s" suffix

    total_uptraffic+=+$(echo "$torrent_stats" | jq -r .snapshot.uploaded_bytes)

    total_downspeed+=+$(echo "$torrent_stats" | jq -r .download_speed.mbps)

    total_downtraffic+=+$(echo "$torrent_stats" | jq -r .snapshot.fetched_bytes)

    printf "%4s %8s %6s %10s %6s %10s %s\n" \
      "$torrent_id" "${torrent_hash:0:8}" \
      "$upload_size" "$upload_speed" \
      "$download_size" "$download_speed" \
      "$torrent_name"

    # exit # debug

    continue

  else

    # verbose -> slow
    torrent_stats=$(curl -s $rqbit_url/torrents/$torrent_id/stats/v1)

    # initializing | live | ...
    torrent_state=$(echo "$torrent_stats" | jq -r .state | head -c5)

    upload_speed=$(echo "$torrent_stats" | jq -r .live.upload_speed.human_readable | tr -d ' ')

    upload_size=$(echo "$torrent_stats" | jq -r .uploaded_bytes | numfmt --to=iec-i --suffix=B)

    download_size=$(echo "$torrent_stats" | jq -r .downloaded_bytes | numfmt --to=iec-i --suffix=B)

    # speed is in MiB/s
    total_upspeed+=+$(echo "$torrent_stats" | jq -r .live.upload_speed.mbps)
    #total_upspeed2+=+$(echo "${upload_speed:0: -3}" | numfmt --from=iec-i) # remove "B/s" suffix

    total_uptraffic+=+$(echo "$torrent_stats" | jq -r .uploaded_bytes)

    total_downspeed+=+$(echo "$torrent_stats" | jq -r .live.download_speed.mbps)

    total_downtraffic+=+$(echo "$torrent_stats" | jq -r .fetched_bytes) # ?

    printf "%4s %5s %6s %10s %s\n" "$torrent_id" "$torrent_state" "$upload_size" "$upload_upspeed" "$torrent_name"

  fi

exit # debug

done < <(
  curl -s $rqbit_url/torrents |
  jq -r '.torrents[] | "\(.id) \(.info_hash)"' | sort -n
  #jq -r '.torrents[] | .id' | sort -n
)

# print summary to stderr -> dont sort the summary

total_upspeed=$(echo "$total_upspeed" | bc | xargs printf "%.2f")MiB/s
#echo "total upspeed: $total_upspeed" >&2

#total_upspeed2=$(echo "$total_upspeed2" | bc | numfmt --to=iec-i)B/s
#echo "total upspeed 2: $total_upspeed2"

total_uptraffic=$(echo "$total_uptraffic" | bc | numfmt --to=iec-i --format=%.6f)B
#echo "total uptraffic: $total_uptraffic" >&2

total_downspeed=$(echo "$total_downspeed" | bc | xargs printf "%.2f")MiB/s
total_downtraffic=$(echo "$total_downtraffic" | bc | numfmt --to=iec-i --format=%.6f)B

echo "total up $total_uptraffic $total_upspeed down $total_downtraffic $total_downspeed" >&2
