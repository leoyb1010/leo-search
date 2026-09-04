#!/bin/sh
set -eu

proxy=${LEO_SEARCH_PROXY:-}
if [ -z "$proxy" ]; then
  proxy_file=${LEO_SEARCH_PROXY_FILE:-"$HOME/.config/leo-search/proxy"}
  [ -f "$proxy_file" ] && proxy=$(sed -n '1p' "$proxy_file")
fi

if [ -n "$proxy" ]; then
  export ALL_PROXY="$proxy"
  export HTTPS_PROXY="$proxy"
  export HTTP_PROXY="$proxy"
fi

exec "$@"
