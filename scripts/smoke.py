#!/usr/bin/env python3
"""Run bounded public retrieval probes. No credentials, browser, or daemon required."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re
import subprocess
import time
from request_budget import RequestBudget
from protocol_check import messages
from evidence_ledger import canonical_url

ROOT = Path(__file__).resolve().parents[1]
ENDPOINTS = {"exa": "https://mcp.exa.ai/mcp", "context7": "https://mcp.context7.com/mcp",
             "tinyfish": "https://agent.tinyfish.ai/mcp"}
BUDGET = RequestBudget()


def http(url: str, payload: dict | None = None) -> str:
    key = (url, json.dumps(payload, sort_keys=True, ensure_ascii=False))
    return BUDGET.run(key, lambda: fetch(url, payload))


def fetch(url: str, payload: dict | None = None, proxy: str | None = None) -> str:
    command = [str(ROOT / "scripts/with_proxy.sh"), "curl", "--fail-with-body",
               "--silent", "--show-error", "--connect-timeout", "5", "--max-time", "20", "--max-filesize", "8388608", "--write-out", "\n%{http_code}",
               "-H", "Accept: " + ("application/json, text/event-stream" if payload is not None else "text/plain")]
    if payload is not None:
        command += ["-H", "Content-Type: application/json", "--data-binary", json.dumps(payload)]
    if proxy:
        command += ["--proxy", proxy]
    result = subprocess.run(command + [url], capture_output=True, text=True, timeout=25)
    if result.returncode in {6, 7, 28} and proxy is None:
        # One bounded fallback, counted against the same hard network budget.
        try:
            settings = subprocess.run(["/usr/sbin/scutil", "--proxy"], capture_output=True, text=True, timeout=3).stdout
            host = re.search(r"HTTPSProxy\s*:\s*(127\.0\.0\.1|localhost)\s", settings)
            port = re.search(r"HTTPSPort\s*:\s*(\d+)", settings)
            if host and port:
                proxy = "http://%s:%s" % (host[1], port[1])
                return BUDGET.run((url, json.dumps(payload, sort_keys=True), proxy), lambda: fetch(url, payload, proxy))
        except (OSError, subprocess.TimeoutExpired):
            pass
    if result.returncode:
        # Deliberately do not log provider error bodies or command arguments.
        raise RuntimeError("HTTP request failed (status %s, curl exit %s)" % (result.stdout.rpartition("\n")[2], result.returncode))
    return result.stdout.rpartition("\n")[0]


def rpc(route: str, method: str, params: dict) -> dict:
    raw = http(ENDPOINTS[route], {"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
    if len(raw) > 8 * 1024 * 1024:
        raise RuntimeError("MCP response exceeds size limit")
    frames = messages(raw)
    replies = [frame for frame in frames if isinstance(frame, dict)
               and type(frame.get('id')) is int and frame['id'] == 1]
    if not replies:
        raise RuntimeError("MCP response ID missing or mismatched")
    data = replies[-1]
    result = data.get("result")
    if data.get('jsonrpc') != '2.0' or "error" in data or not isinstance(result, dict):
        raise RuntimeError("Invalid MCP response envelope")
    if result.get("isError"):
        raise RuntimeError("MCP tool returned isError")
    return result


def text_content(result: dict) -> str:
    content = result.get("content", [])
    if not isinstance(content, list) or any(not isinstance(c, dict) for c in content):
        raise RuntimeError("Invalid MCP content array")
    text = []
    for item in content:
        if item.get('type') == 'text':
            if not isinstance(item.get('text'), str):
                raise RuntimeError("Invalid MCP text content")
            text.append(item['text'])
    return "\n".join(text)


def reader_document(raw: str, url: str) -> tuple[str, list[str]]:
    """Separate Reader-owned provenance from untrusted extracted page text."""
    outer = raw.lstrip()
    parsed = None
    structured = outer.startswith(("{", "["))
    if structured:
        parsed = json.loads(outer)
    elif (outer.startswith(('event:', 'data:', ':')) and all(
            not line or line.startswith(('event:', 'data:', 'id:', 'retry:', ':'))
            for line in outer.replace('\r\n', '\n').split('\n'))):
        # Classify only the outer wire envelope. A Markdown page may itself
        # contain data: examples, which are never transport metadata.
        frames = messages(outer)
        if frames:
            structured = True
            parsed = frames[-1]
    if structured:
        if not isinstance(parsed, dict):
            raise RuntimeError("Jina returned an invalid response shape")
        data = parsed.get("data", parsed)
        if not isinstance(data, dict) or not isinstance(data.get("content"), str):
            raise RuntimeError("Jina returned no readable content")
        if not isinstance(data.get("url"), str):
            raise RuntimeError("Jina returned no source URL")
        source = canonical_url(data["url"])
        return "URL Source: " + source + "\n" + str(data.get("warning", "")) + "\n" + data["content"], [source]
    # Jina's text response has a metadata preamble followed by Markdown Content.
    # Stop on body text: a page can itself contain forged URL Source lines.
    sources = []
    body_boundary = False
    for line in raw.splitlines():
        if line.startswith('Markdown Content:'):
            body_boundary = True
            break
        if line.startswith('URL Source:'):
            sources.append(canonical_url(line.partition(':')[2].strip()))
        elif line and not line.startswith(('Title:', 'Published Time:', 'Warning:')):
            break
    sources = sorted(set(sources)) if body_boundary else []
    if len(sources) > 1:
        raise RuntimeError('Jina returned conflicting source metadata')
    return raw, sources


def reader_content(raw: str, url: str) -> str:
    return reader_document(raw, url)[0]


def source_urls(content: str) -> list[str]:
    urls = re.findall(r"(?im)^(?:URL|Source|URL Source):\s*(https?://[^\s<>]+)", content)
    return sorted({canonical_url(url) for url in urls})


def probe(case: dict) -> dict:
    started = time.monotonic()
    row = {"id": case["id"], "route": case["route"], "question": case["question"],
           "stage": "retrieval", "status": "unverified"}
    if case.get("fallback_for"):
        row["fallback_for"] = case["fallback_for"]
    try:
        route = case["route"]
        if route == "jina":
            content, reader_sources = reader_document(http("https://r.jina.ai/" + case["url"]), case["url"])
        else:
            tools = rpc(route, "tools/list", {}).get("tools", [])
            if not isinstance(tools, list) or len(tools) > 1000 or any(not isinstance(t, dict) or not isinstance(t.get('name'), str) for t in tools):
                raise RuntimeError("Invalid MCP tool inventory")
            row["tools_visible"] = len(tools)
            names = {t["name"] for t in tools}
            if route == "exa":
                tool, args = "web_search_exa", {"query": case["question"], "numResults": 3}
            elif route == "context7":
                resolve = next((n for n in names if n in {"resolve-library-id", "resolve_library_id"}), None)
                if resolve is None:
                    raise RuntimeError("library resolver unavailable")
                resolved = text_content(rpc(route, "tools/call", {"name": resolve, "arguments": {
                    "libraryName": case["library"], "query": case["question"]}}))
                ids = re.findall(r"Context7-compatible library ID:\s*(/[^\s]+)", resolved)
                if not ids:
                    raise RuntimeError("no resolved library ID")
                row["library_id"] = ids[0]
                tool = next((n for n in names if n in {"query-docs", "query_docs"}), "query-docs")
                args = {"libraryId": ids[0], "query": case["question"]}
            else:
                # TinyFish OAuth is owned by the host. Never infer retrieval from metadata.
                raise RuntimeError("host-authenticated tool call required")
            if tool not in names:
                raise RuntimeError("expected tool unavailable")
            content = text_content(rpc(route, "tools/call", {"name": tool, "arguments": args}))
        # Only provider source fields count as citations, never URLs inside example code.
        urls = reader_sources if route == "jina" else source_urls(content)
        row.update({"characters": len(content), "source_urls": urls[:12],
                    "cached_snapshot": "cached snapshot" in content.lower(),
                    "checks": {"nonempty": len(content.strip()) >= 80,
                               "source_present": bool(urls),
                               "topic_match": any(x.casefold() in content.casefold() for x in case["keywords"])}})
        if route == "jina":
            # A fetched, different resource is not proof of the requested page.
            # Redirects are reported as a gap rather than silently relabeled.
            row["checks"]["source_matches_requested"] = canonical_url(case["url"]) in urls
        row["status"] = "pass" if all(row["checks"].values()) else "fail"
        row["semantic_accuracy"] = "not_scored"
    except (RuntimeError, ValueError, OSError, subprocess.TimeoutExpired) as error:
        row["status"] = "unavailable"
        row["reason"] = str(error)[:180]
    row["latency_ms"] = round((time.monotonic() - started) * 1000)
    return row


def main() -> int:
    global BUDGET
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", action="store_true", help="Run all 20 frozen public questions")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--fallback-only", action="store_true", help="Use known official URLs for selected failed search cases")
    parser.add_argument("--case", action="append", help="Rerun only named cases; avoids repeating successful calls")
    parser.add_argument("--max-requests", type=int, default=8, help="Hard network budget including discovery; default 8")
    args = parser.parse_args()
    if args.max_requests < 1:
        parser.error("--max-requests must be positive")
    BUDGET = RequestBudget(args.max_requests)
    cases = json.loads((ROOT / "benchmarks/questions.json").read_text())
    if args.case:
        unknown = set(args.case) - {c["id"] for c in cases}
        if unknown:
            parser.error("unknown case IDs: " + ", ".join(sorted(unknown)))
        cases = [c for c in cases if c["id"] in args.case]
    elif not args.benchmark:
        cases = [next(c for c in cases if c["route"] == route) for route in ("exa", "context7", "jina")]
    if args.fallback_only:
        if not args.case or any(not c.get("fallback_url") for c in cases):
            parser.error("--fallback-only needs selected cases with a known official fallback URL")
        cases = [{**c, "route": "jina", "url": c["fallback_url"], "fallback_for": c["route"]} for c in cases]
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(probe, cases))
    report = {"schema_version": 1, "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "scope": "public_retrieval_contracts", "semantic_accuracy": "not_scored",
              "passed": sum(r["status"] == "pass" for r in rows), "total": len(rows), "cases": rows,
              "requests": {"used": BUDGET.calls, "limit": BUDGET.limit, "reused": BUDGET.cache_hits},
              "boundaries": ["TinyFish needs a host-authenticated search call; OAuth metadata is not proof.",
                             "Account-bound social sources and answer-level accuracy are not measured."]}
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    print(rendered)
    return 0 if report["passed"] == len(rows) else 2


if __name__ == "__main__":
    raise SystemExit(main())
