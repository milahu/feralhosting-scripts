#!/usr/bin/env bash

# monitor network traffic of a process
# https://unix.stackexchange.com/a/6929/295986

set -eu

curl -s http://localhost:3034/stats | jq
exit

pid=$(pgrep rqbit || true)

# why? blame nix-shell
if [ -z "$pid" ]; then
  # cat: /proc/3114813/io: No such file or directory
  #pid=3114813
  echo "error: not found pid of process" >&2
  exit 1
fi

while true; do

  eval $(cat /proc/$pid/io | sed 's/: /=/')

  time=$(date --utc +%s)

  # payload traffic: up 1.450163TiB + down 688.649911MiB

  # 1718872971,853.397302MiB,-87.720849GiB
  #out=$((wchar - write_bytes)); in=$((rchar - read_bytes))

  # 1718873132,108.031573GiB,1.829787TiB
  #out=$wchar; in=$rchar

  # 1718873187,107.232708GiB,1.915926TiB
  #out=$write_bytes; in=$read_bytes

  # 1718873228,1.916148TiB,107.256169GiB
  #out=$read_bytes; in=$write_bytes

  # 1718873309,1.830446TiB,108.136342GiB
  out=$rchar; in=$wchar

  out=$(echo $out | numfmt --to=iec-i --format=%.3f)B
  in=$(echo $in | numfmt --to=iec-i --format=%.3f)B

  #echo "$time,$out,$in"
  echo "$out $in"

  break # dont loop

  sleep 1

done
