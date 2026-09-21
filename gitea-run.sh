#!/bin/sh
set -eux
exec ~/bin/gitea-1.22.0-linux-amd64 web --work-path ~/var/lib/gitea
# cd ~/var/lib/gitea
# serv --config custom/conf/app.ini
