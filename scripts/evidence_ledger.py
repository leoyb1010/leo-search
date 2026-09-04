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
    return normalized


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
            else:
                records[key] = item
    except (json.JSONDecodeError, ValueError) as error:
        print(f"evidence-ledger: {error}", file=sys.stderr)
        return 2

    for item in records.values():
        print(json.dumps(item, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
