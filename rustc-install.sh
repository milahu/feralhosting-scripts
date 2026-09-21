#!/usr/bin/env bash

# https://www.feralhosting.com/wiki/slots/install-deb
# https://packages.debian.org/bookworm/rustc

set -e
set -x

version=1.63.0+dfsg1-2

wget http://ftp.uk.debian.org/debian/pool/main/r/rustc/rustc_${version}_amd64.deb

dpkg -x rustc_${version}_amd64.deb ~/rustc
ln -sr ~/rustc/usr/bin/* ~/bin

