#!/usr/bin/env bash

ip a s | grep " inet " | grep $UID | awk '{ print $2 }' | cut -d/ -f1
