#!/usr/bin/env bash

rqbit_url=http://localhost:3030

level="$1"

case "$level" in
  trace|debug|info|warn|error)
    :
  ;;
  *)
    echo "error: unknown level ${level@Q}. possible values: trace, debug, info, warn, error"
    exit 1
  ;;
esac

curl -d "$level" "$rqbit_url/rust_log"
