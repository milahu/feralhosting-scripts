#!/usr/bin/env bash

# https://www.feralhosting.com/wiki/software/qbittorrent
# https://bitbucket.org/feralio/wiki/raw/HEAD/src/wiki/software/qbittorrent/install

f=$HOME/.config/qBittorrent/qBittorrent.conf

if [ -e $f ]; then
  echo "error: config exists: $f"
  echo "hint:"
  echo "mv $f $f.bak.$(date -Is)"
  exit 1
fi

# https://www.reddit.com/r/unRAID/comments/180ou0b/psa_if_you_cant_login_to_qbittorrent_pass/
user=admin
pass=adminadmin
salt=ARQ77eY1NUZaQsuDHbIMCA==
hmac=0WMRkYTUWVT9wVvdDtHAjU9b3b7uB8NR1Gur2hmQCvCDpm39Q+PsJRJPaCU51dEiz+dTzh8qbPsL8WkFljQYFQ==

# Configure
user=$(whoami)
salt="$(dd if=/dev/urandom count=4 bs=4 2>/dev/null | base64)"
pass="$(tr -dc a-z0-9 </dev/urandom | head -c 20 ; echo '')"
hmac="$(php -r "echo base64_encode(hash_pbkdf2(\"sha512\", \"$pass\", base64_decode(\"$salt\"), 100000, 0, true));")"

mkdir -p ~/.config/qBittorrent
cat >$f <<EOF
[LegalNotice]
Accepted=true
[BitTorrent]
Session\AsyncIOThreadsCount=1
Session\HashingThreadsCount=1
[Preferences]
Bittorrent\MaxConnecs=40
Bittorrent\MaxConnecsPerTorrent=-1
Bittorrent\MaxUploads=-1
Bittorrent\MaxUploadsPerTorrent=-1
Queueing\QueueingEnabled=false
WebUI\Username=$user
WebUI\Password_PBKDF2="@ByteArray($salt:$hmac)"
WebUI\Port=9001
WebUI\MaxAuthenticationFailCount=60
Downloads\SavePath=$HOME/private/qbittorrent/data
EOF

# Report
echo qBittorrent has been successfully installed. It will be running in five minutes.
echo
echo URL: https://$(hostname -f)/$(whoami)/qbittorrent/
echo Username: $user
echo Password: $pass
