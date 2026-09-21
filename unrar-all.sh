#!/usr/bin/env bash

set -eux

mkdir -p trash

shopt -s nullglob

# support up to 9999 parts

# todo trap exit. print failed
failed=()

#trash_dir=trash
#failed_dir=failed

for a in *.part0001.rar *.part001.rar *.part01.rar *.part1.rar; do
  echo ----------------------
  echo "extracting: $a"
  sleep 3 # time to abort
  if ! unrar x "$@" "$a"; then
    echo "error: failed to extract $a"
    failed+=("$a")
    continue
  fi
  # move all parts to trash
  b=${a%.part*.rar} # base
  echo "moving: $b*"
  [ -e "$b.sfv" ] && mv "$b.sfv" trash
  # ls "$b".*.part[0-9]*.rar
  # todo grep more strict
  # todo use find . -name ...
  ls | grep -F "$b.part" | grep ".rar$" |
  while read -d$'\n' f; do
    echo "done: $f"
    mv "$f" trash
  done
done

# fixme dont process failed .part*.rar files again

for a in *.rar; do
  echo ----------------------
  echo "extracting: $a"
  sleep 3 # time to abort
  if ! unrar x "$@" "$a"; then
    echo "error: failed to extract $a"
    failed+=("$a")
    continue
  fi
  mv "$a" trash
  b=${a%.rar} # base
  [ -e "$b.sfv" ] && mv "$b.sfv" trash
  for p in "$b".r[0-9] "$b".r[0-9][0-9] "$b".r[0-9][0-9][0-9] "$b".r[0-9][0-9][0-9][0-9]; do
    mv "$p" trash
  done
done

for f in "${failed[@]}"; do
  echo "failed: $f"
done
