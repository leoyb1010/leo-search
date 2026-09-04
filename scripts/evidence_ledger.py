#!/usr/bin/env python3
"""Normalize JSONL search evidence and collapse exact source duplicates."""

from __future__ import annotations

import hashlib
import json
import sys
from collections import OrderedDict
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


TRACKING_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid"}


def canonical_url(value: str) -> str:
    parts = urlsplit(value.strip())
    if parts.scheme.lower() not in {"http", "https"} or not parts.netloc:
        raise ValueError(f"unsupported URL: {value}")
    query = [
        (key, item)
        for key, item in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in TRACKING_KEYS
    ]
    path = parts.path or "/"
    if path != "/":
        path = path.rstrip("/")
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(sorted(query)), ""))


def normalize(record: dict[str, object]) -> dict[str, object]:
    url = record.get("url")
    if not isinstance(url, str) or not url.strip():
        raise ValueError("each evidence record requires a URL")
    normalized = dict(record)
    normalized["canonical_url"] = canonical_url(url)
    content = normalized.get("content")
    normalized["content_hash"] = (
        hashlib.sha256(content.encode("utf-8")).hexdigest()
        if isinstance(content, str) and content
        else None
    )
    normalized["duplicate_count"] = 1
    normalized["source_urls"] = [url]
    claims = record.get("claim_ids", [])
    if not isinstance(claims, list) or any(not isinstance(x, str) for x in claims):
        raise ValueError("claim_ids must be an array of strings")
    normalized["claim_ids"] = claims
    support = record.get("support", "unknown")
    if not isinstance(support, str) or support not in {"supports", "contradicts", "context", "unknown"}:
        raise ValueError("invalid support value")
    normalized["support_values"] = [support]
    upstream = record.get("upstream_source")
    normalized["upstream_sources"] = []
    if upstream is not None:
        if not isinstance(upstream, str):
            raise ValueError("upstream_source must be a URL")
        normalized["upstream_source"] = canonical_url(upstream)
        normalized["upstream_sources"] = [normalized["upstream_source"]]
    return normalized


def group_sources(items: list[dict[str, object]]) -> None:
    """Group known shared provenance, without asserting independence otherwise."""
    parents = list(range(len(items)))
    seen: dict[str, int] = {}

    def find(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    for index, item in enumerate(items):
        keys = ["url:" + str(item["canonical_url"])]
        if item["content_hash"]:
            keys.append("content:" + str(item["content_hash"]))
        keys.extend("url:" + str(url) for url in item["upstream_sources"])
        for key in keys:
            if key in seen:
                parents[find(index)] = find(seen[key])
            seen[key] = index
    groups: dict[int, list[dict[str, object]]] = {}
    for index, item in enumerate(items):
        groups.setdefault(find(index), []).append(item)
    for group in groups.values():
        urls = sorted({str(item["canonical_url"]) for item in group})
        group_id = hashlib.sha256("\n".join(urls).encode()).hexdigest()[:16]
        for item in group:
            item["evidence_group"] = group_id
            item["group_urls"] = urls
            item["independence"] = "shared_provenance" if len(urls) > 1 else "unverified"


def main() -> int:
    records: OrderedDict[tuple[str, object], dict[str, object]] = OrderedDict()
    try:
        for line_number, line in enumerate(sys.stdin, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"line {line_number} is not a JSON object")
            item = normalize(value)
            key = (str(item["canonical_url"]), item["content_hash"])
            if key in records:
                records[key]["duplicate_count"] = int(records[key]["duplicate_count"]) + 1
                for field in ("source_urls", "claim_ids", "support_values", "upstream_sources"):
                    records[key][field] = sorted(set(records[key][field]) | set(item[field]))
                if len(records[key]["support_values"]) > 1:
                    records[key]["support"] = "unknown"
            else:
                records[key] = item
    except (json.JSONDecodeError, ValueError) as error:
        print(f"evidence-ledger: {error}", file=sys.stderr)
        return 2

    group_sources(list(records.values()))
    for item in records.values():
        print(json.dumps(item, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
