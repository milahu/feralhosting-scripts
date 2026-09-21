#!/usr/bin/env bash

shopt -s dotglob

# 2134284301307   total
du -b -s -c * | sort -n | tee du.$(date --utc +%Y%m%dT%H%M%SZ).txt

# 2.0T    total
# du -h -s -c * | sort -h | tee du.$(date --utc +%Y%m%dT%H%M%SZ).txt

# 2.2T    total
# du --si -s -c * | sort -h | tee du.$(date --utc +%Y%m%dT%H%M%SZ).txt
