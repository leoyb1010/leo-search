#!/usr/bin/env python3
"""Opt-in native MCP inventory; optionally one TinyFish search, with no model turn."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import selectors
import signal
import subprocess
import tempfile
import time


def isolated_args(config: str) -> list[str]:
    args = ['codex', 'app-server']
    # Read table names only. Overrides apply to this subprocess, never to saved settings.
    for family, quoted, bare in re.findall(r'^\[(plugins|mcp_servers)\.(?:"([^"\n]+)"|([A-Za-z0-9_@-]+))\]\s*$', config, re.M):
        name = quoted or bare
        if not re.fullmatch(r'[A-Za-z0-9_@-]+', name):
            raise ValueError('unsupported config identifier; native probe stopped')
        if family == 'plugins' and name == 'leo-search@personal':
            continue
        args += ['-c', family + '.' + name + '.enabled=false']
    return args


def summarize(servers: list[dict], oauth_rejected: bool = False) -> list[dict]:
    rows = []
    for server in servers:
        if not server['name'].startswith('leo-search-'):
            continue
        names = sorted(server.get('tools', {}))
        row = {'name': server['name'], 'auth_status': server.get('authStatus'),
               'tools': names, 'stage': 'tools_visible' if names else 'unavailable',
               'retrieval_verified': False}
        if server['name'] == 'leo-search-tinyfish' and oauth_rejected:
            row['reason'] = 'OAuth refresh rejected; reauthorization required'
        elif not names:
            row['reason'] = 'No tools exposed; stored auth metadata is not proof'
        rows.append(row)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--search', action='store_true', help='Perform one fixed public TinyFish search using host OAuth')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    config_path = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))) / 'config.toml'
    command = isolated_args(config_path.read_text())
    report = {'schema_version': 1, 'measured_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
              'scope': 'host_native_mcp', 'model_turns': 0, 'tool_calls': 0, 'servers': []}
    with tempfile.TemporaryFile(mode='w+') as log, tempfile.TemporaryDirectory(prefix='leo-search-probe-') as directory:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log,
                                   text=True, bufsize=1, start_new_session=True)
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        def call(ident, method, params):
            process.stdin.write(json.dumps({'id': ident, 'method': method, 'params': params}) + '\n')
            process.stdin.flush()
            end = time.monotonic() + 45
            while time.monotonic() < end:
                for key, _ in selector.select(1):
                    line = key.fileobj.readline()
                    if not line:
                        raise RuntimeError('native server exited')
                    message = json.loads(line)
                    if message.get('id') == ident:
                        if 'error' in message:
                            raise RuntimeError('native RPC failed: ' + method)
                        return message['result']
                    if 'id' in message and 'method' in message:
                        raise RuntimeError('interactive input required; probe stopped')
            raise RuntimeError('native RPC timed out: ' + method)
        try:
            call(1, 'initialize', {'clientInfo': {'name': 'leo-search-probe', 'version': '1.4.0'},
                                   'capabilities': {'experimentalApi': True}})
            process.stdin.write('{"method":"initialized"}\n'); process.stdin.flush()
            servers, cursor, ident = [], None, 2
            while True:
                page = call(ident, 'mcpServerStatus/list', {'detail': 'toolsAndAuthOnly', 'limit': 100, 'cursor': cursor})
                servers.extend(page['data']); cursor = page.get('nextCursor'); ident += 1
                if not cursor:
                    break
            log.flush(); log.seek(0)
            report['servers'] = summarize(servers, 'invalid_grant' in log.read())
            tiny = next((r for r in report['servers'] if r['name'] == 'leo-search-tinyfish'), None)
            if args.search:
                if not tiny or 'search' not in tiny['tools']:
                    raise RuntimeError('TinyFish search unavailable; use Exa fallback')
                # Ephemeral execution context is discarded; no persisted task or model run.
                thread = call(ident, 'thread/start', {'cwd': directory, 'ephemeral': True,
                              'approvalPolicy': 'never', 'sandbox': 'read-only'})
                report['tool_calls'] = 1
                result = call(ident + 1, 'mcpServer/tool/call', {'threadId': thread['thread']['id'],
                    'server': 'leo-search-tinyfish', 'tool': 'search', 'arguments': {
                        'query': 'Model Context Protocol official tools specification',
                        'include_domains': 'modelcontextprotocol.io', 'language': 'en'}})
                body = '\n'.join(x.get('text', '') for x in result.get('content', []) if x.get('type') == 'text')
                tiny['retrieval_verified'] = not result.get('isError') and len(body) > 80 and 'modelcontextprotocol.io' in body
                tiny['stage'] = 'retrieval' if tiny['retrieval_verified'] else 'unavailable'
                tiny['characters'] = len(body)
                if not tiny['retrieval_verified']:
                    raise RuntimeError('TinyFish returned no usable source content')
        except (ValueError, OSError, RuntimeError) as error:
            report['error'] = str(error)
        finally:
            selector.close()
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL); process.wait()
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    print(rendered)
    return 2 if report.get('error') or any(r['stage'] == 'unavailable' for r in report['servers']) else 0


if __name__ == '__main__':
    raise SystemExit(main())
