#!/usr/bin/env bash
# no: apptainer: /lib/x86_64-linux-gnu/libc.so.6: version `GLIBC_2.28' not found (required by apptainer)
# debian buster is from year 2020 (circa)
# ... or make the new version work with bubblewrap by passing a new glibc

# $ ldd bin/apptainer | grep libc
# bin/apptainer: /lib/x86_64-linux-gnu/libc.so.6: version `GLIBC_2.28' not found (required by bin/apptainer)
#         libc.so.6 => /lib/x86_64-linux-gnu/libc.so.6 (0x00007f8dd9200000)

# https://apptainer.org/docs/admin/main/installation.html
set -eux
pname=apptainer
version=1.3.2
wget https://github.com/$pname/$pname/releases/download/v1.3.2/${pname}_${version}_amd64.deb
mkdir -p ~/opt
rm -rf ~/opt/${pname}
dpkg -x ${pname}_${version}_amd64.deb ~/opt/${pname}
shopt -s nullglob
ln -srf -t ~/bin ~/opt/${pname}/usr/bin/*
