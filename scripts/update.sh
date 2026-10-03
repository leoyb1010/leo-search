#!/bin/sh
set -eu

plugin_dir=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
if [ ! -e "$plugin_dir/.git" ] || ! git -C "$plugin_dir" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "$plugin_dir is not a Git checkout; cannot update automatically." >&2
  exit 69
fi

git -C "$plugin_dir" pull --ff-only
exec "$plugin_dir/scripts/install.sh"
