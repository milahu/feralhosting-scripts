#!/usr/bin/env bash
# https://packages.debian.org/buster/jq
set -eux

function install_pkg() {

url="$1"
bname=$(basename "$url" .deb)

if [ "${url:0:4}" != "http" ]; then
  url=http://ftp.uk.debian.org/debian/pool/main/$url
fi

echo bname $bname

wget -N $url

mkdir -p ~/opt
rm -rf ~/opt/${bname}
dpkg -x $bname.deb ~/opt/${bname}
shopt -s nullglob
if [ -d ~/opt/${bname}/usr/bin ]; then ln -srf -t ~/bin ~/opt/${bname}/usr/bin/*; fi
}

install_pkg j/jq/jq_1.5+dfsg-2+b1_amd64.deb
install_pkg j/jq/libjq1_1.5+dfsg-2+b1_amd64.deb
install_pkg libo/libonig/libonig5_6.9.1-1_amd64.deb

# todo
# patchelf bin/jq --replace-needed libjq.so.1 ~/opt/libjq1_1.5+dfsg-2+b1_amd64/usr/lib/x86_64-linux-gnu/libjq.so.1.0.4
# patchelf bin/jq --replace-needed libonig.so.5 ~/opt/libonig5_6.9.1-1_amd64/usr/lib/x86_64-linux-gnu/libonig.so.5.0.0

# $ find opt/ -name 'libjq.so.1*' -type f
# opt/libjq1/usr/lib/x86_64-linux-gnu/libjq.so.1.0.4
