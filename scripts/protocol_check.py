#!/usr/bin/env python3
"""Validate doctor responses without printing provider payloads or credentials."""
import json
import sys
from urllib.parse import urlsplit


def messages(raw):
    if raw.lstrip().startswith('{'):
        return [json.loads(raw)]
    values, data = [], []
    for line in raw.replace('\r\n', '\n').split('\n') + ['']:
        if not line:
            if data:
                values.append(json.loads('\n'.join(data)))
                data = []
        elif line.startswith('data:'):
            data.append(line[5:].lstrip(' '))
    return values


def valid_initialize(raw):
    try:
        matches = [value for value in messages(raw) if isinstance(value, dict)
                   and type(value.get('id')) is int and value['id'] == 1]
        if not matches:
            return False
        value = matches[-1]
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
        value = json.loads(raw)
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
