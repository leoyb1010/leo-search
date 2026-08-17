#!/bin/sh
set -eu

repo_url="${LEO_SEARCH_REPO_URL:-https://github.com/leoyb1010/leo-search.git}"
destination="${HOME}/plugins/leo-search"
parent="${HOME}/plugins"

command -v git >/dev/null 2>&1 || {
  echo "git is required." >&2
  exit 69
}

mkdir -p "$parent"
if [ -e "$destination" ]; then
  if [ ! -d "$destination/.git" ]; then
    echo "$destination exists and is not a Git checkout; refusing to overwrite it." >&2
    exit 73
  fi
  current_origin=$(git -C "$destination" remote get-url origin 2>/dev/null || true)
  case "$current_origin" in
    "$repo_url"|https://github.com/leoyb1010/leo-search|git@github.com:leoyb1010/leo-search.git)
      git -C "$destination" pull --ff-only
      ;;
    *)
      echo "$destination belongs to a different repository: $current_origin" >&2
      exit 73
      ;;
  esac
else
  git clone --depth 1 "$repo_url" "$destination"
fi

exec "$destination/scripts/install.sh"
