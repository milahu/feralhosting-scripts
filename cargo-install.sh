#!/usr/bin/env bash

# https://www.feralhosting.com/wiki/slots/install-deb
# https://packages.debian.org/bookworm/cargo

set -e
set -x

version=0.66.0+ds1-1

wget http://ftp.uk.debian.org/debian/pool/main/c/cargo/cargo_${version}_amd64.deb

dpkg -x cargo_${version}_amd64.deb ~/cargo
ln -sr ~/cargo/usr/bin/* ~/bin

