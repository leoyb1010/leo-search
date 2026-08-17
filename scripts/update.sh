#!/bin/sh
set -eu

plugin_dir=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
if [ ! -d "$plugin_dir/.git" ]; then
  echo "$plugin_dir is not a Git checkout; cannot update automatically." >&2
  exit 69
fi

git -C "$plugin_dir" pull --ff-only
exec "$plugin_dir/scripts/install.sh"
