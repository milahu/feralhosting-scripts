#!/usr/bin/env bash

set -eu

# add ~/bin to $PATH
source ~/.profile

{
  #proc_totals=$(~/scripts/rqbit-stats.sh)

  # redirect stderr to stdout, drop stdout
  # https://stackoverflow.com/a/549776/10440128
  #totals=$(./scripts/rqbit-list.sh 2>&1 >&- | sed 's/^total //')
  totals=$(~/scripts/rqbit-list.sh 2>&1 >/dev/null | sed 's/^total //')

  #echo "$(date +%Y-%m-%dT%H:%M:%S%z) $totals - proc: $proc_totals"
  echo "$(date +%Y-%m-%dT%H:%M:%S%z) $totals"

} >> ~/scripts/rqbit-log-totals.sh.log
