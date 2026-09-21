#!/usr/bin/env bash

# https://github.com/go-gitea/gitea/releases/latest

# example: 1.22.0
version=$(curl -s -I https://github.com/go-gitea/gitea/releases/latest | grep -i ^location | tr -d $'\r' | cut -d/ -f8 | tail -c+2)

wget https://github.com/go-gitea/gitea/releases/download/v$version/gitea-$version-linux-amd64.xz

xz -d gitea-$version-linux-amd64.xz

chmod +x gitea-$version-linux-amd64

echo done gitea-$version-linux-amd64
