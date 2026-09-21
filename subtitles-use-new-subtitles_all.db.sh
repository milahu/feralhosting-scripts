#!/usr/bin/env bash

set -eux

src_db_path="$1"

src_db_dir="$(dirname "$src_db_path")"
src_db_dir="$(realpath "$src_db_dir")"

src_db_name="$(basename "$src_db_path")"

dst_db_name='subtitles_all.db'

dst_dir="$HOME/.config/subtitles"
dst_dir="$(realpath "$dst_dir")"

if [ "$src_db_dir" != "$dst_dir" ]; then
  mkdir -p "$dst_dir"
  mv -f "$src_db_path" "$dst_dir"
fi

if [ "$src_db_name" != "$dst_db_name" ]; then
  ln -s -f "$src_db_name" "$dst_dir/$dst_db_name"
fi

# TODO on success: delete old db files
