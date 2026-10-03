#!/usr/bin/env python3
"""Validate doctor responses without printing provider payloads or credentials."""
import json
import math
import sys
from urllib.parse import urlsplit


def load_json(raw):
    """Reject non-finite numbers, invalid Unicode and deeply nested provider data."""
    def invalid_constant(_value):
        raise ValueError("JSON requires finite numbers; use null or a finite value")
    def unique_object(pairs):
        result = {}
        for key, item in pairs:
            if key in result:
                raise ValueError("JSON object contains duplicate fields; keep one value per field")
            result[key] = item
        return result
    try:
        value = json.loads(raw, parse_constant=invalid_constant, object_pairs_hook=unique_object)
    except RecursionError:
        raise ValueError("JSON nesting exceeds 64 levels; flatten nested metadata") from None
    pending = [(value, 0)]
    while pending:
        item, depth = pending.pop()
        if depth > 64:
            raise ValueError("JSON nesting exceeds 64 levels; flatten nested metadata")
        if isinstance(item, dict):
            pending.extend((child, depth + 1) for pair in item.items() for child in pair)
        elif isinstance(item, list):
            pending.extend((child, depth + 1) for child in item)
        elif isinstance(item, float) and not math.isfinite(item):
            raise ValueError("JSON requires finite numbers; use null or a finite value")
        elif isinstance(item, str):
            try:
                item.encode('utf-8')
            except UnicodeError:
                raise ValueError("JSON contains invalid Unicode; replace unpaired surrogate escapes") from None
    return value


def wire_lines(raw):
    """SSE permits CR, LF, CRLF and one initial UTF-8 BOM (WHATWG §9.2.5)."""
    return raw.removeprefix('\ufeff').replace('\r\n', '\n').replace('\r', '\n').split('\n')


def messages(raw):
    raw = raw.removeprefix('\ufeff')
    if raw.lstrip().startswith('{'):
        return [load_json(raw)]
    values, data = [], []
    for line in wire_lines(raw) + ['']:
        if not line:
            if data:
                values.append(load_json('\n'.join(data)))
                data = []
        elif line.startswith('data:'):
            data.append(line[5:].lstrip(' '))
    return values


def valid_initialize(raw):
    try:
        matches = [value for value in messages(raw) if isinstance(value, dict)
                   and type(value.get('id')) is int and value['id'] == 1]
        if len(matches) != 1:
            return False
        value = matches[0]
        result = value.get('result')
        if value.get('jsonrpc') != '2.0' or 'error' in value or not isinstance(result, dict):
            return False
        info = result.get('serverInfo')
        return bool(isinstance(result.get('protocolVersion'), str) and result['protocolVersion']
                    and isinstance(info, dict) and isinstance(info.get('name'), str) and info['name'])
    except (ValueError, TypeError):
        return False


def valid_oauth_metadata(raw):
    try:
        value = load_json(raw)
        if not isinstance(value, dict) or value.get('resource') != 'https://agent.tinyfish.ai/mcp':
            return False
        servers = value.get('authorization_servers')
        if not isinstance(servers, list) or not servers:
            return False
        for server in servers:
            if not isinstance(server, str):
                return False
            url = urlsplit(server)
            if url.scheme != 'https' or not url.hostname or url.username or url.password or url.fragment:
                return False
        return True
    except (ValueError, TypeError):
        return False


if __name__ == '__main__':
    validator = {'initialize': valid_initialize, 'oauth': valid_oauth_metadata}.get(sys.argv[1] if len(sys.argv) > 1 else '')
    raw = sys.stdin.read(1024 * 1024 + 1)
    raise SystemExit(0 if validator and len(raw) <= 1024 * 1024 and validator(raw) else 1)
