#!/bin/sh

# https://www.feralhosting.com/wiki/software/nginx#start-stop-restart

# list
ps x | grep nginx | grep -v grep

# kill
pkill -fu "$(whoami)" 'nginx'

# TODO is this different?
# killall nginx
