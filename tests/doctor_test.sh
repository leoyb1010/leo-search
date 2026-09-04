#!/bin/sh
set -eu

root=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
temporary=$(mktemp -d "${TMPDIR:-/tmp}/leo-search-doctor-test.XXXXXX")
trap 'rm -rf "$temporary"' EXIT HUP INT TERM

mkdir "$temporary/bin"

# The single-quoted expressions belong to the generated fake curl script.
# shellcheck disable=SC2016
printf '%s\n' '#!/bin/sh' \
  'case "$*" in' \
  '  *--proxy*mcp.exa.ai*)' \
  '    printf "event: message\\ndata: %s\\n\\n%s" "${FAKE_EXA_BODY:-{\"jsonrpc\":\"2.0\",\"result\":{\"protocolVersion\":\"2025-06-18\",\"serverInfo\":{\"name\":\"fake\"}}}}" "${FAKE_PROXY_STATUS:-200}"' \
  '    ;;' \
  '  *--proxy*oauth-protected-resource*)' \
  '    printf "%s\\n%s" "${FAKE_TINYFISH_BODY:-{\"resource\":\"https://agent.tinyfish.ai/mcp\",\"authorization_servers\":[\"https://clerk.tinyfish.ai\"]}}" "${FAKE_PROXY_STATUS:-200}"' \
  '    ;;' \
  '  *mcp.exa.ai*)' \
  '    printf "event: message\\ndata: %s\\n\\n%s" "${FAKE_EXA_BODY:-{\"protocolVersion\":\"2025-06-18\"}}" "${FAKE_EXA_STATUS:-200}"' \
  '    ;;' \
  '  *mcp.context7.com*)' \
  '    printf "event: message\\ndata: {\"jsonrpc\":\"2.0\",\"result\":{\"protocolVersion\":\"2025-06-18\",\"serverInfo\":{\"name\":\"fake\"}}}\\n\\n200"' \
  '    ;;' \
  '  *oauth-protected-resource*)' \
  '    printf "%s\\n%s" "${FAKE_TINYFISH_BODY:-{\"resource\":\"https://agent.tinyfish.ai/mcp\",\"authorization_servers\":[\"https://clerk.tinyfish.ai\"]}}" "${FAKE_TINYFISH_STATUS:-200}"' \
  '    ;;' \
  '  *--proxy*) printf "%s" "${FAKE_PROXY_STATUS:-200}" ;;' \
  '  *) printf "%s" "${FAKE_JINA_STATUS:-200}" ;;' \
  'esac' > "$temporary/bin/curl"
chmod +x "$temporary/bin/curl"

# The single-quoted expressions belong to the generated fake scutil script.
# shellcheck disable=SC2016
printf '%s\n' '#!/bin/sh' \
  'if [ "${FAKE_SYSTEM_PROXY:-0}" = "1" ]; then' \
  '  printf "<dictionary> {\\n  HTTPSProxy : 127.0.0.1\\n  HTTPSPort : 7897\\n}\\n"' \
  'fi' > "$temporary/bin/scutil"
chmod +x "$temporary/bin/scutil"

run_doctor() {
  set +e
  LEO_SEARCH_PROXY_FILE="$temporary/no-proxy" PATH="$temporary/bin:/usr/bin:/bin" "$root/scripts/doctor.sh" "$@" > "$temporary/output" 2>&1
  status=$?
  set -e
}

FAKE_EXA_STATUS=503 run_doctor
test "$status" -eq 2
grep -q 'WARN Exa MCP' "$temporary/output"

FAKE_EXA_STATUS=200 FAKE_EXA_BODY='{}' run_doctor
test "$status" -eq 2
grep -q 'invalid MCP initialize response' "$temporary/output"

FAKE_EXA_STATUS=200 FAKE_EXA_BODY='{"protocolVersion":"2025-06-18"}' run_doctor
test "$status" -eq 2
grep -q 'invalid MCP initialize response' "$temporary/output"

valid_exa_body='{"jsonrpc":"2.0","result":{"protocolVersion":"2025-06-18","serverInfo":{"name":"fake"}}}'
FAKE_EXA_STATUS=200 FAKE_EXA_BODY="$valid_exa_body" run_doctor
test "$status" -eq 0
grep -q 'OK   Exa MCP' "$temporary/output"
grep -q 'INFO TinyFish MCP.*OAuth metadata' "$temporary/output"

FAKE_EXA_STATUS=200 FAKE_EXA_BODY="$valid_exa_body" FAKE_TINYFISH_STATUS=503 run_doctor
test "$status" -eq 2
grep -q 'WARN TinyFish MCP.*HTTP 503' "$temporary/output"

FAKE_EXA_STATUS=200 FAKE_EXA_BODY="$valid_exa_body" FAKE_TINYFISH_STATUS=200 FAKE_JINA_STATUS=302 run_doctor
test "$status" -eq 2
grep -q 'WARN Jina Reader.*HTTP 302' "$temporary/output"

FAKE_EXA_STATUS=200 FAKE_EXA_BODY="$valid_exa_body" FAKE_TINYFISH_STATUS=200 FAKE_JINA_STATUS=000 FAKE_SYSTEM_PROXY=1 FAKE_PROXY_STATUS=200 run_doctor
test "$status" -eq 0
grep -q 'OK   Jina Reader.*HTTP 200 via system-proxy' "$temporary/output"

FAKE_EXA_STATUS=200 FAKE_EXA_BODY="$valid_exa_body" FAKE_TINYFISH_STATUS=200 FAKE_JINA_STATUS=000 FAKE_SYSTEM_PROXY=0 FAKE_PROXY_STATUS=200 LEO_SEARCH_PROXY=socks5h://127.0.0.1:7898 run_doctor
test "$status" -eq 0
grep -q 'OK   Jina Reader.*HTTP 200 via system-proxy' "$temporary/output"

FAKE_EXA_STATUS=000 FAKE_EXA_BODY="$valid_exa_body" FAKE_TINYFISH_STATUS=000 FAKE_JINA_STATUS=200 FAKE_SYSTEM_PROXY=0 FAKE_PROXY_STATUS=200 LEO_SEARCH_PROXY=socks5h://127.0.0.1:7898 run_doctor
test "$status" -eq 0
grep -q 'OK   Exa MCP.*via system-proxy' "$temporary/output"
grep -q 'INFO TinyFish MCP.*via system-proxy' "$temporary/output"

printf '%s\n' '#!/bin/sh' 'exit 0' > "$temporary/bin/opencli"
chmod +x "$temporary/bin/opencli"
FAKE_EXA_STATUS=200 FAKE_EXA_BODY="$valid_exa_body" FAKE_TINYFISH_STATUS=200 FAKE_JINA_STATUS=200 FAKE_SYSTEM_PROXY=0 run_doctor
test "$status" -eq 0
grep -q 'INFO OpenCLI.*installed; extension readiness is account-bound' "$temporary/output"
if grep -q 'OK   OpenCLI' "$temporary/output"; then
  echo 'OpenCLI must not be reported ready from executable presence alone' >&2
  exit 1
fi

FAKE_EXA_STATUS=200 FAKE_EXA_BODY="$valid_exa_body" FAKE_TINYFISH_STATUS=200 FAKE_JINA_STATUS=200 FAKE_SYSTEM_PROXY=0 run_doctor --json
test "$status" -eq 0
python3 - "$temporary/output" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)

assert report["schemaVersion"] == 2
assert report["result"] == "ok"
assert report["warnings"] == 0
assert report["deep"] is False
assert report["retrieval_verified"] is False
assert report["scope"] == "connectivity_only"
assert any(r["section"] == "resource safety" for r in report["routes"])
assert next(r for r in report["routes"] if r["label"] == "TinyFish MCP")["status"] == "info"
labels = {route["label"] for route in report["routes"]}
assert {"Exa MCP", "Context7 MCP", "TinyFish MCP", "Jina Reader"} <= labels
PY

echo 'doctor tests passed'
