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
  code=$(curl --connect-timeout 5 --max-time 12 --silent --show-error --output /dev/null --write-out '%{http_code}' "$url" 2>/dev/null || printf '000')
  case "$code" in
    2??)
      printf 'OK   %-14s HTTP %s\n' "$label" "$code"
      ;;
    *)
      printf 'WARN %-14s HTTP %s: %s\n' "$label" "$code" "$url"
      warnings=$((warnings + 1))
      ;;
  esac
}

mcp_status() {
  label=$1
  url=$2
  payload='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"leo-search-doctor","version":"1.0"}}}'
  response=$(curl --connect-timeout 5 --max-time 12 --silent --show-error \
    --header 'Content-Type: application/json' \
    --header 'Accept: application/json, text/event-stream' \
    --data "$payload" --write-out '\n%{http_code}' "$url" 2>/dev/null) || response='000'
  code=$(printf '%s\n' "$response" | tail -n 1)
  body=$(printf '%s\n' "$response" | sed '$d')
  case "$code" in
    2??)
      if printf '%s' "$body" | grep -Eq '"jsonrpc"[[:space:]]*:[[:space:]]*"2\.0"' &&
        printf '%s' "$body" | grep -q '"result"' &&
        printf '%s' "$body" | grep -q '"protocolVersion"' &&
        printf '%s' "$body" | grep -q '"serverInfo"'; then
        printf 'OK   %-14s MCP initialize HTTP %s\n' "$label" "$code"
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
  agent-reach doctor || warnings=$((warnings + 1))
fi

if [ "$deep" -eq 1 ] && command -v gh >/dev/null 2>&1; then
  section "authenticated routes"
  if gh auth status >/dev/null 2>&1; then
    echo "OK   GitHub authentication"
  else
    echo "WARN GitHub CLI installed but not authenticated"
    warnings=$((warnings + 1))
  fi
fi

printf '\nResult: %s warning(s).\n' "$warnings"
if [ "$warnings" -gt 0 ]; then
  exit 2
fi
