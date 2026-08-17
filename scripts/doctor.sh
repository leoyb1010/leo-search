#!/bin/sh
set -u

deep=0
if [ "${1:-}" = "--deep" ]; then
  deep=1
elif [ "$#" -gt 0 ]; then
  echo "usage: $0 [--deep]" >&2
  exit 64
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

endpoint_status() {
  label=$1
  url=$2
  code=$(curl --connect-timeout 5 --max-time 12 --silent --show-error --output /dev/null --write-out '%{http_code}' "$url" 2>/dev/null || printf '000')
  case "$code" in
    000|000000)
      printf 'WARN %-14s unreachable: %s\n' "$label" "$url"
      warnings=$((warnings + 1))
      ;;
    *)
      printf 'OK   %-14s HTTP %s\n' "$label" "$code"
      ;;
  esac
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
endpoint_status "Exa MCP" "https://mcp.exa.ai/mcp"
endpoint_status "Context7 MCP" "https://mcp.context7.com/mcp"
endpoint_status "Jina Reader" "https://r.jina.ai/https://example.com"

section "optional local routes"
command_status "GitHub" gh
command_status "mcporter" mcporter
command_status "Agent Reach" agent-reach
command_status "OpenCLI" opencli
command_status "yt-dlp" yt-dlp

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
  agent-reach doctor || warnings=$((warnings + 1))
fi

printf '\nResult: %s warning(s).\n' "$warnings"
if [ "$warnings" -gt 0 ]; then
  exit 2
fi
