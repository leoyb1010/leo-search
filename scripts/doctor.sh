#!/bin/sh
set -u

deep=0
json=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --deep) deep=1 ;;
    --json) json=1 ;;
    *) echo "usage: $0 [--deep] [--json]" >&2; exit 64 ;;
  esac
  shift
done

if [ "$json" -eq 1 ]; then
  if ! command -v python3 >/dev/null 2>&1; then
    echo "doctor --json requires python3" >&2
    exit 69
  fi
  temporary=$(mktemp "${TMPDIR:-/tmp}/leo-search-doctor.XXXXXX") || exit 70
  trap 'rm -f "$temporary"' EXIT HUP INT TERM
  set +e
  if [ "$deep" -eq 1 ]; then
    "$0" --deep >"$temporary" 2>&1
  else
    "$0" >"$temporary" 2>&1
  fi
  status=$?
  set -e
  python3 - "$temporary" "$status" "$deep" <<'PY'
import json
import re
import sys

path, status, deep = sys.argv[1], int(sys.argv[2]), bool(int(sys.argv[3]))
section = None
routes = []
agent_lines = []
warnings = 0
with open(path, encoding="utf-8") as handle:
    for raw in handle:
        line = raw.rstrip("\n")
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
            continue
        if section == "Agent Reach doctor" and not line.startswith("Result:"):
            agent_lines.append(line)
            continue
        result = re.match(r"^Result: (\d+) warning", line)
        if result:
            warnings = int(result.group(1))
            continue
        match = re.match(r"^(OK|WARN|INFO)\s+(.+?)\s{2,}(.*)$", line)
        if not match and section == "resource safety":
            match = re.match(r"^(OK|WARN|INFO)\s+(.+)$", line)
            if match:
                state, detail = match.groups()
                label = ("browser processes" if "browser-automation processes" in detail or "headless" in detail
                         else "browser controllers" if "controller" in detail else "search jobs")
                routes.append({"section": section, "label": label,
                               "status": {"OK": "ok", "WARN": "warning", "INFO": "info"}[state],
                               "stage": "resource_check", "detail": detail})
            continue
        if match:
            state, label, detail = match.groups()
            routes.append({
                "section": section,
                "label": label.strip(),
                "status": {"OK": "ok", "WARN": "warning", "INFO": "info"}[state],
                "detail": detail.strip(),
                "stage": ("oauth_metadata" if "OAuth metadata" in detail else
                          "initialize" if "initialize" in detail else
                          "http" if detail.startswith("HTTP") else "installed"),
                "retrieval_verified": False,
            })

try:
    agent_report = json.loads("\n".join(agent_lines)) if agent_lines else None
except json.JSONDecodeError:
    agent_report = {"status": "unparsed", "detail": "Agent Reach did not return valid JSON"}

print(json.dumps({
    "schemaVersion": 2,
    "scope": "connectivity_only",
    "retrieval_verified": False,
    "result": "ok" if status == 0 else "warning",
    "warnings": warnings,
    "deep": deep,
    "routes": routes,
    "agent_reach": agent_report,
}, ensure_ascii=False, indent=2))
PY
  exit "$status"
fi

warnings=0

section() {
  printf '\n[%s]\n' "$1"
}

command_status() {
  label=$1
  command_name=$2
  if command -v "$command_name" >/dev/null 2>&1; then
    resolved=$(command -v "$command_name")
    printf 'OK   %-14s %s\n' "$label" "$resolved"
  else
    printf 'INFO %-14s not installed (optional)\n' "$label"
  fi
}

opencli_status() {
  if command -v opencli >/dev/null 2>&1; then
    printf 'INFO %-14s installed; extension readiness is account-bound\n' 'OpenCLI'
  else
    printf 'INFO %-14s not installed (optional)\n' 'OpenCLI'
  fi
}

endpoint_status() {
  label=$1
  url=$2
  route=direct
  code=$(curl --connect-timeout 5 --max-time 12 --silent --show-error --output /dev/null --write-out '%{http_code}' "$url" 2>/dev/null || true)
  [ -n "$code" ] || code=000
  case "$code" in
    2??) ;;
    *)
      proxy=$(system_https_proxy)
      if [ -n "$proxy" ]; then
        route=system-proxy
        code=$(curl --proxy "$proxy" --connect-timeout 5 --max-time 12 --silent --show-error --output /dev/null --write-out '%{http_code}' "$url" 2>/dev/null || true)
        [ -n "$code" ] || code=000
      fi
      ;;
  esac
  case "$code" in
    2??)
      printf 'OK   %-14s HTTP %s via %s\n' "$label" "$code" "$route"
      ;;
    *)
      printf 'WARN %-14s HTTP %s: %s\n' "$label" "$code" "$url"
      warnings=$((warnings + 1))
      ;;
  esac
}

system_https_proxy() {
  if [ -n "${LEO_SEARCH_PROXY:-}" ]; then
    printf '%s\n' "$LEO_SEARCH_PROXY"
    return
  fi
  proxy_file=${LEO_SEARCH_PROXY_FILE:-"$HOME/.config/leo-search/proxy"}
  if [ -f "$proxy_file" ]; then
    proxy_value=$(sed -n '1p' "$proxy_file")
    case "$proxy_value" in
      http://*|https://*|socks5://*|socks5h://*) printf '%s\n' "$proxy_value"; return ;;
    esac
  fi
  scutil_command=$(command -v scutil 2>/dev/null || true)
  if [ -z "$scutil_command" ] && [ -x /usr/sbin/scutil ]; then
    scutil_command=/usr/sbin/scutil
  fi
  if [ -n "$scutil_command" ]; then
    proxy_host=$("$scutil_command" --proxy 2>/dev/null | awk '/HTTPSProxy/ {print $3; exit}')
    proxy_port=$("$scutil_command" --proxy 2>/dev/null | awk '/HTTPSPort/ {print $3; exit}')
    case "$proxy_host" in
      127.0.0.1|localhost)
        case "$proxy_port" in
          ''|*[!0-9]*) ;;
          *) printf 'http://%s:%s\n' "$proxy_host" "$proxy_port" ;;
        esac
        ;;
    esac
  fi
}

mcp_status() {
  label=$1
  url=$2
  route=direct
  payload='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"leo-search-doctor","version":"1.0"}}}'
  response=$(curl --connect-timeout 5 --max-time 12 --silent --show-error \
    --header 'Content-Type: application/json' \
    --header 'Accept: application/json, text/event-stream' \
    --data "$payload" --write-out '\n%{http_code}' "$url" 2>/dev/null) || response='000'
  code=$(printf '%s\n' "$response" | tail -n 1)
  body=$(printf '%s\n' "$response" | sed '$d')
  case "$code" in
    2??) ;;
    *)
      proxy=$(system_https_proxy)
      if [ -n "$proxy" ]; then
        route=system-proxy
        response=$(curl --proxy "$proxy" --connect-timeout 5 --max-time 12 --silent --show-error \
          --header 'Content-Type: application/json' \
          --header 'Accept: application/json, text/event-stream' \
          --data "$payload" --write-out '\n%{http_code}' "$url" 2>/dev/null) || response='000'
        code=$(printf '%s\n' "$response" | tail -n 1)
        body=$(printf '%s\n' "$response" | sed '$d')
      fi
      ;;
  esac
  case "$code" in
    2??)
      if printf '%s' "$body" | grep -Eq '"jsonrpc"[[:space:]]*:[[:space:]]*"2\.0"' &&
        printf '%s' "$body" | grep -q '"result"' &&
        printf '%s' "$body" | grep -q '"protocolVersion"' &&
        printf '%s' "$body" | grep -q '"serverInfo"'; then
        printf 'OK   %-14s MCP initialize HTTP %s via %s\n' "$label" "$code" "$route"
      else
        printf 'WARN %-14s invalid MCP initialize response\n' "$label"
        warnings=$((warnings + 1))
      fi
      ;;
    *)
      printf 'WARN %-14s MCP initialize HTTP %s: %s\n' "$label" "$code" "$url"
      warnings=$((warnings + 1))
      ;;
  esac
}

oauth_metadata_status() {
  label=$1
  url=$2
  route=direct
  response=$(curl --connect-timeout 5 --max-time 12 --silent --show-error \
    --write-out '\n%{http_code}' "$url" 2>/dev/null) || response='000'
  code=$(printf '%s\n' "$response" | tail -n 1)
  body=$(printf '%s\n' "$response" | sed '$d')
  case "$code" in
    2??) ;;
    *)
      proxy=$(system_https_proxy)
      if [ -n "$proxy" ]; then
        route=system-proxy
        response=$(curl --proxy "$proxy" --connect-timeout 5 --max-time 12 --silent --show-error \
          --write-out '\n%{http_code}' "$url" 2>/dev/null) || response='000'
        code=$(printf '%s\n' "$response" | tail -n 1)
        body=$(printf '%s\n' "$response" | sed '$d')
      fi
      ;;
  esac
  case "$code" in
    2??)
      if printf '%s' "$body" | grep -q '"resource"' &&
        printf '%s' "$body" | grep -q '"authorization_servers"'; then
        printf 'INFO %-14s OAuth metadata HTTP %s via %s; authentication and retrieval unverified\n' "$label" "$code" "$route"
      else
        printf 'WARN %-14s invalid OAuth metadata response\n' "$label"
        warnings=$((warnings + 1))
      fi
      ;;
    *)
      printf 'WARN %-14s OAuth metadata HTTP %s: %s\n' "$label" "$code" "$url"
      warnings=$((warnings + 1))
      ;;
  esac
}

rss_parser_status() {
  if command -v xmllint >/dev/null 2>&1; then
    printf 'OK   %-14s %s\n' 'RSS parser' "$(command -v xmllint)"
  elif command -v python3 >/dev/null 2>&1; then
    printf 'OK   %-14s Python xml.etree\n' 'RSS parser'
  else
    printf 'INFO %-14s not installed (optional)\n' 'RSS parser'
  fi
}

headless_processes() {
  ps -axo pid=,ppid=,etime=,rss=,comm= 2>/dev/null | awk '
    BEGIN { IGNORECASE=1 }
    /chrome-headless-shell|google chrome for testing|headless[[:space:]_-]*chrom/ { print }
  '
}

automation_controllers() {
  ps -axo pid=,ppid=,etime=,rss=,args= 2>/dev/null | awk '
    BEGIN { IGNORECASE=1 }
    /playwright-mcp|@playwright\/mcp|patchright|crawl4ai/ && !/awk/ { print }
  '
}

section "remote routes"
mcp_status "Exa MCP" "https://mcp.exa.ai/mcp"
mcp_status "Context7 MCP" "https://mcp.context7.com/mcp"
oauth_metadata_status "TinyFish MCP" "https://agent.tinyfish.ai/.well-known/oauth-protected-resource/mcp"
endpoint_status "Jina Reader" "https://r.jina.ai/https://example.com"

section "optional local routes"
command_status "GitHub" gh
command_status "mcporter" mcporter
command_status "Agent Reach" agent-reach
opencli_status
command_status "yt-dlp" yt-dlp
command_status "Bilibili" bili
rss_parser_status

section "resource safety"
headless=$(headless_processes)
if [ -n "$headless" ]; then
  printf 'WARN browser-automation processes detected:\n%s\n' "$headless"
  warnings=$((warnings + 1))
else
  echo "OK   no Chrome-for-Testing or headless-Chromium browser process"
fi

controllers=$(automation_controllers)
if [ -n "$controllers" ]; then
  printf 'INFO browser-capable controller exists but has no browser child:\n%s\n' "$controllers"
else
  echo "OK   no browser-automation controller process"
fi

if command -v launchctl >/dev/null 2>&1; then
  jobs=$(launchctl print "gui/$(id -u)" 2>/dev/null | awk 'BEGIN { IGNORECASE=1 } /leo-search.*(heartbeat|daemon)|agent-reach.*heartbeat/ { print }')
  if [ -n "$jobs" ]; then
    printf 'WARN search heartbeat/daemon job detected:\n%s\n' "$jobs"
    warnings=$((warnings + 1))
  else
    echo "OK   no Leo Search or Agent Reach heartbeat job"
  fi
fi

if [ "$deep" -eq 1 ] && command -v agent-reach >/dev/null 2>&1; then
  section "Agent Reach doctor"
  agent-reach doctor --json || warnings=$((warnings + 1))
fi

if [ "$deep" -eq 1 ] && command -v gh >/dev/null 2>&1; then
  section "authenticated routes"
  if gh api user --jq .login >/dev/null 2>&1; then
    echo "OK   GitHub API authentication"
  else
    echo "WARN GitHub CLI installed but not authenticated"
    warnings=$((warnings + 1))
  fi
fi

printf '\nResult: %s warning(s).\n' "$warnings"
if [ "$warnings" -gt 0 ]; then
  exit 2
fi
