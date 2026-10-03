#!/bin/sh
set -eu

plugin_dir=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
expected_dir="${HOME}/plugins/leo-search"
marketplace_file="${HOME}/.agents/plugins/marketplace.json"

if [ "$plugin_dir" != "$expected_dir" ]; then
  echo "Leo Search must live at $expected_dir for the personal Codex marketplace." >&2
  echo "Use scripts/bootstrap.sh for a one-command installation." >&2
  exit 64
fi

command -v python3 >/dev/null 2>&1 || {
  echo "python3 is required to update the marketplace safely." >&2
  exit 69
}
command -v codex >/dev/null 2>&1 || {
  echo "Codex CLI is required." >&2
  exit 69
}

python3 "$plugin_dir/scripts/marketplace.py" "$marketplace_file"

marketplace_name=$(python3 - "$marketplace_file" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as handle:
    print(json.load(handle).get("name", "personal"))
PY
)

codex plugin add "leo-search@${marketplace_name}"
set +e
"${plugin_dir}/scripts/doctor.sh"
doctor_rc=$?
set -e
case "$doctor_rc" in
  0) ;;
  2)
    echo "Leo Search installed with optional-route warnings; core plugin remains enabled."
    ;;
  *)
    exit "$doctor_rc"
    ;;
esac
echo "Leo Search installed. Start a new Codex task to load its skill and MCP tools."
