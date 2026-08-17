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
  '  *mcp.exa.ai*)' \
  '    printf "event: message\\ndata: %s\\n\\n%s" "${FAKE_EXA_BODY:-{\"protocolVersion\":\"2025-06-18\"}}" "${FAKE_EXA_STATUS:-200}"' \
  '    ;;' \
  '  *mcp.context7.com*)' \
  '    printf "event: message\\ndata: {\"protocolVersion\":\"2025-06-18\"}\\n\\n200"' \
  '    ;;' \
  '  *) printf "200" ;;' \
  'esac' > "$temporary/bin/curl"
chmod +x "$temporary/bin/curl"

run_doctor() {
  set +e
  PATH="$temporary/bin:/usr/bin:/bin" "$root/scripts/doctor.sh" > "$temporary/output" 2>&1
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
test "$status" -eq 0
grep -q 'OK   Exa MCP' "$temporary/output"

printf '%s\n' '#!/bin/sh' 'exit 0' > "$temporary/bin/opencli"
chmod +x "$temporary/bin/opencli"
FAKE_EXA_STATUS=200 FAKE_EXA_BODY='{"protocolVersion":"2025-06-18"}' run_doctor
test "$status" -eq 0
grep -q 'INFO OpenCLI.*installed; extension readiness is account-bound' "$temporary/output"
if grep -q 'OK   OpenCLI' "$temporary/output"; then
  echo 'OpenCLI must not be reported ready from executable presence alone' >&2
  exit 1
fi

echo 'doctor tests passed'
