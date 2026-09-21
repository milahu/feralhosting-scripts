#!/bin/sh

# https://bitbucket.org/feralio/wiki/raw/HEAD/src/wiki/software/qbittorrent/install
bits=$(( $(id -u) << 1 ))
upper=$(( $bits >> 8 ))
lower=$(( $bits - ($upper << 8) + 1 ))
ip="10.0.$upper.$lower"
echo "containers ip: $ip"

set -x

ip a s | grep "  inet " | grep $(id -u)

# ip a s | grep "scope global" | grep -w u$(id -u)

# curl -s http://httpbin.org/ip
pub=$(curl -s http://httpbin.org/ip |
  grep origin | cut -d'"' -f4)
echo "public ip address: $pub"

ip a s | grep -B10 "inet $pub"

# ping -c1 $(hostname -f)

resolveip $(hostname -f)

route | grep default
