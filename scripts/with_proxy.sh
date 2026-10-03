#!/bin/sh
set -eu

if [ "$#" -eq 0 ]; then
  echo "usage: with_proxy.sh <command> [args...]" >&2
  exit 64
fi

proxy=${LEO_SEARCH_PROXY:-}
if [ -z "$proxy" ]; then
  proxy_file=${LEO_SEARCH_PROXY_FILE:-"$HOME/.config/leo-search/proxy"}
  [ -f "$proxy_file" ] && proxy=$(sed -n '1p' "$proxy_file")
fi

if [ -n "$proxy" ]; then
  export ALL_PROXY="$proxy"
  export HTTPS_PROXY="$proxy"
  export HTTP_PROXY="$proxy"
  # curl accepts http_proxy only in lowercase; lowercase inherited values can
  # otherwise override the user's explicit per-command proxy selection.
  export all_proxy="$proxy"
  export https_proxy="$proxy"
  export http_proxy="$proxy"
fi

exec "$@"
