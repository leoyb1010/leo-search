#!/bin/sh
set -eu

plugin_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
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

python3 - "$marketplace_file" <<'PY'
import json
import os
import shutil
import sys
import tempfile
import time

path = os.path.abspath(os.path.expanduser(sys.argv[1]))
os.makedirs(os.path.dirname(path), exist_ok=True)

if os.path.exists(path):
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
else:
    data = {"name": "personal", "interface": {"displayName": "Personal"}, "plugins": []}

data.setdefault("name", "personal")
data.setdefault("interface", {"displayName": "Personal"})
plugins = data.setdefault("plugins", [])
entry = {
    "name": "leo-search",
    "source": {"source": "local", "path": "./plugins/leo-search"},
    "policy": {"installation": "AVAILABLE", "authentication": "ON_USE"},
    "category": "Productivity",
}

for index, existing in enumerate(plugins):
    if existing.get("name") == "leo-search":
        plugins[index] = entry
        break
else:
    plugins.append(entry)

rendered = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
current = ""
if os.path.exists(path):
    with open(path, "r", encoding="utf-8") as handle:
        current = handle.read()

if rendered != current:
    if os.path.exists(path):
        backup = f"{path}.bak.{time.strftime('%Y%m%d-%H%M%S')}"
        shutil.copy2(path, backup)
        print(f"Marketplace backup: {backup}")
    fd, temporary = tempfile.mkstemp(prefix="marketplace.", suffix=".json", dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(rendered)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    print(f"Marketplace updated: {path}")
else:
    print(f"Marketplace already current: {path}")

print(data["name"])
PY

marketplace_name=$(python3 - "$marketplace_file" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as handle:
    print(json.load(handle).get("name", "personal"))
PY
)

codex plugin add "leo-search@${marketplace_name}"
"${plugin_dir}/scripts/doctor.sh"
echo "Leo Search installed. Start a new Codex task to load its skill and MCP tools."
