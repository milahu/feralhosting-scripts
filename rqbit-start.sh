#!/usr/bin/env bash

set -x

#exec rqbit server start --persistence-filename ~/.cache/rqbit/state ~/rqbit
#exec rqbit server start --persistence-filename ~/.cache/rqbit/state ~/rqbit --http-api-listen-addr 0.0.0.0:3030
#exec rqbit --http-api-listen-addr 0.0.0.0:3030 --disable-upnp server start --persistence-filename ~/.cache/rqbit/state ~/rqbit
#exec rqbit -v error --disable-upnp --tcp-min-port 6000 --tcp-max-port 65535 server start --persistence-filename ~/.cache/rqbit/state ~/rqbit

export RUST_BACKTRACE=1
# export RUST_BACKTRACE=full

a=(

rqbit

# options

--disable-upnp-port-forward

# main branch
--tcp-min-port 6000
--tcp-max-port 6099

# utp branch
# --listen-port 6000
# --experimental-enable-utp-listen

--http-api-listen-addr 127.0.0.1:3034

#--worker-threads 1
--worker-threads 8

# 8 -> 22 GB # default
# 2 -> 9 GB
# --max-blocking-threads 3
--max-blocking-threads 2

# -v error # quiet
-v info # verbose

# command
server start

# command options

--fastresume

# --persistence-filename ~/.cache/rqbit/state
--persistence-location ~/.cache/rqbit

# output_folder
~/rqbit
)

set -x

while true; do
  #tmp=$(mktemp)
  # "${a[@]}"
  [ -e ~/.cache/rqbit/session.json ] &&
  cp ~/.cache/rqbit/session.json \
     ~/.cache/rqbit/session.json.bak.$(date -Is)
  mkdir -p log
  "${a[@]}" 2>&1 |
  tee log/rqbit.$(date -Is).log
  #2>&1 |
  #tee -a /dev/stderr |
  #tail -n 200 >$tmp
  # rqbit crashed
  #mv $tmp log/rqbit.crash.$(date -Is).txt
  ~/scripts/screen-dump.sh rqbit
  mv "$(ls -t screen.rqbit.*.txt | head -n1)" log/
  # wait before restart
  sleep 5m
done

# no. use ssh port forwarding: ssh -L 3030:127.0.0.1:3030 ...
# listen on all interfaces
# http://pontus.feralhosting.com:3030/web/
#exec rqbit --http-api-listen-addr 0.0.0.0:3030 --disable-upnp --tcp-min-port 6000 --tcp-max-port 65535 server start --persistence-filename ~/.cache/rqbit/state ~/rqbit
