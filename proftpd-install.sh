#!/usr/bin/env bash

set -e
set -x

wget -qO ~/proftpd.tar.gz ftp://ftp.proftpd.org/distrib/source/proftpd-1.3.6.tar.gz
tar xf ~/proftpd.tar.gz -C ~/
cd proftpd-*
install_user=$(whoami) install_group=$(whoami) ./configure --prefix=$HOME/proftpd --enable-openssl --enable-dso --enable-nls --enable-ctrls --with-shared=mod_ratio:mod_readme:mod_sftp:mod_tls:mod_ban:mod_shaper
make && make install
mkdir -p ~/proftpd/etc/sftp/authorized_keys ~/proftpd/etc/keys ~/proftpd/ssl
cd && rm -rf proftpd-* proftpd.tar.gz



