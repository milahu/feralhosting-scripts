#!/bin/sh

cat ~/proftpd/var/proftpd.pid | xargs kill && sleep 15 && ~/proftpd/sbin/proftpd -c ~/proftpd/etc/proftpd.conf
