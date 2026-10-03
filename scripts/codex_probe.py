#!/usr/bin/env python3
"""Opt-in native MCP inventory; optionally one TinyFish search, with no model turn."""
from __future__ import annotations
import argparse
import json
from protocol_check import load_json
import os
from pathlib import Path
import re
import selectors
import signal
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlsplit
from report_output import write_report
from evidence_ledger import canonical_url
from smoke import text_content
try:
    import tomllib
except ImportError:
    print('Native probe requires Python 3.11 or newer; no server was started.', file=sys.stderr)
    raise SystemExit(2)


def isolated_args(config: str) -> list[str]:
    """Parse all TOML table forms; quote keys in process-local CLI overrides."""
    parsed = tomllib.loads(config)
    args = ['codex', 'app-server']
    for family in ('plugins', 'mcp_servers'):
        entries = parsed.get(family, {})
        if not isinstance(entries, dict):
            raise ValueError('invalid config table; native probe stopped')
        for name in entries:
            if family == 'plugins' and name == 'leo-search@personal':
                continue
            args += ['-c', family + '.' + json.dumps(name) + '.enabled=false']
    return args


class RpcPeer:
    """Bounded binary framing: a readable partial line must never block forever."""
    def __init__(self, process, timeout=45, overall_timeout=90):
        self.process = process
        self.timeout = timeout
        self.deadline = time.monotonic() + overall_timeout
        self.buffer = b''
        self.selector = selectors.DefaultSelector()
        self.selector.register(process.stdout, selectors.EVENT_READ)

    def send(self, message):
        self.process.stdin.write((json.dumps(message) + '\n').encode())
        self.process.stdin.flush()

    def close(self):
        self.selector.close()

    def call(self, ident, method, params):
        self.send({'id': ident, 'method': method, 'params': params})
        end = min(time.monotonic() + self.timeout, self.deadline)
        while time.monotonic() < end:
            while b'\n' in self.buffer:
                line, self.buffer = self.buffer.split(b'\n', 1)
                if not line.strip():
                    continue
                try:
                    message = load_json(line)
                except (ValueError, UnicodeError):
                    raise RuntimeError('invalid native RPC frame') from None
                if not isinstance(message, dict):
                    raise RuntimeError('invalid native RPC message')
                if 'id' in message and 'method' in message:
                    raise RuntimeError('interactive input required; probe stopped')
                if type(message.get('id')) is type(ident) and message.get('id') == ident:
                    if 'error' in message or 'result' not in message:
                        raise RuntimeError('native RPC failed: ' + method)
                    return message['result']
            remaining = end - time.monotonic()
            if remaining <= 0:
                break
            for key, _ in self.selector.select(min(1, remaining)):
                chunk = os.read(key.fd, 65536)
                if not chunk:
                    raise RuntimeError('native server exited')
                self.buffer += chunk
                if len(self.buffer) > 1024 * 1024:
                    raise RuntimeError('native RPC frame exceeds 1 MiB')
        raise RuntimeError('native RPC timed out: ' + method)


def summarize(servers: list[dict], oauth_rejected: bool = False) -> list[dict]:
    if not isinstance(servers, list):
        raise RuntimeError('invalid native server inventory')
    rows = []
    for server in servers:
        if not isinstance(server, dict) or not isinstance(server.get('name'), str):
            raise RuntimeError('invalid native server inventory entry')
        if not server['name'].startswith('leo-search-'):
            continue
        tools = server.get('tools', {})
        if not isinstance(tools, dict) or any(not isinstance(name, str) for name in tools):
            raise RuntimeError('invalid native tool inventory')
        names = sorted(tools)
        row = {'name': server['name'], 'auth_status': server.get('authStatus'),
               'tools': names, 'stage': 'tools_visible' if names else 'unavailable',
               'retrieval_verified': False}
        if server['name'] == 'leo-search-tinyfish' and oauth_rejected:
            row['stage'] = 'unavailable'
            row['reason'] = 'OAuth refresh rejected; reauthorization required'
        elif not names:
            row['reason'] = 'No tools exposed; stored auth metadata is not proof'
        rows.append(row)
    return rows


def emit_report(report, output):
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if output:
        try:
            write_report(output, rendered)
        except OSError:
            print(rendered)
            print("Could not save report; complete results are on stdout. Existing output was preserved.", file=sys.stderr)
            return 2
    print(rendered)
    return 2 if report.get('error') or any(r['stage'] == 'unavailable' for r in report['servers']) else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--search', action='store_true', help='Perform one fixed public TinyFish search using host OAuth')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    config_path = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))) / 'config.toml'
    try:
        command = isolated_args(config_path.read_text())
    except (OSError, ValueError):
        parser.exit(2, 'Native probe could not read a valid host configuration. No server was started.\n')
    report = {'schema_version': 1, 'measured_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
              'scope': 'host_native_mcp', 'model_turns': 0, 'tool_calls': 0, 'servers': []}
    with tempfile.TemporaryFile(mode='w+') as log, tempfile.TemporaryDirectory(prefix='leo-search-probe-') as directory:
        try:
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log,
                                       cwd=directory, bufsize=0, start_new_session=True)
        except OSError:
            report['error'] = 'Could not start native server; check Codex CLI installation.'
            return emit_report(report, args.output)
        peer = RpcPeer(process)
        call = peer.call
        try:
            call(1, 'initialize', {'clientInfo': {'name': 'leo-search-probe', 'version': '1.4.0'},
                                   'capabilities': {'experimentalApi': True}})
            peer.send({'method': 'initialized'})
            servers, cursor, ident, seen_cursors = [], None, 2, set()
            while True:
                page = call(ident, 'mcpServerStatus/list', {'detail': 'toolsAndAuthOnly', 'limit': 100, 'cursor': cursor})
                if not isinstance(page, dict) or not isinstance(page.get('data'), list):
                    raise RuntimeError('invalid native server inventory')
                servers.extend(page['data']); cursor = page.get('nextCursor'); ident += 1
                if cursor:
                    if not isinstance(cursor, str) or cursor in seen_cursors or len(seen_cursors) >= 10:
                        raise RuntimeError('native inventory pagination did not terminate')
                    seen_cursors.add(cursor)
                if not cursor:
                    break
            log.flush(); log.seek(0)
            report['servers'] = summarize(servers, 'invalid_grant' in log.read())
            required = {'leo-search-exa', 'leo-search-context7', 'leo-search-tinyfish'}
            if not required.issubset({r['name'] for r in report['servers']}):
                raise RuntimeError('expected Leo Search routes are missing from native inventory')
            tiny = next((r for r in report['servers'] if r['name'] == 'leo-search-tinyfish'), None)
            if args.search:
                if not tiny or tiny['stage'] == 'unavailable' or 'search' not in tiny['tools']:
                    raise RuntimeError('TinyFish search unavailable; use Exa fallback')
                # Ephemeral execution context is discarded; no persisted task or model run.
                thread = call(ident, 'thread/start', {'cwd': directory, 'ephemeral': True,
                              'approvalPolicy': 'never', 'sandbox': 'read-only'})
                if (not isinstance(thread, dict) or not isinstance(thread.get('thread'), dict)
                        or not isinstance(thread['thread'].get('id'), str) or not thread['thread']['id']):
                    raise RuntimeError('invalid native thread handoff')
                report['tool_calls'] = 1
                result = call(ident + 1, 'mcpServer/tool/call', {'threadId': thread['thread']['id'],
                    'server': 'leo-search-tinyfish', 'tool': 'search', 'arguments': {
                        'query': 'Model Context Protocol official tools specification',
                        'include_domains': 'modelcontextprotocol.io', 'language': 'en'}})
                if not isinstance(result, dict):
                    raise RuntimeError('invalid native tool result')
                body = text_content(result)
                # Native providers also return Markdown citations, not only
                # explicit Source fields. Validate URL authorities, not a
                # substring that a lookalike hostname can satisfy.
                urls = [canonical_url(url.rstrip(').,;]}'))
                        for url in re.findall(r'https?://[^\s<>"`]+', body)]
                tiny['retrieval_verified'] = not result.get('isError') and len(body) > 80 and any(
                    urlsplit(url).hostname == 'modelcontextprotocol.io' for url in urls)
                tiny['stage'] = 'retrieval' if tiny['retrieval_verified'] else 'unavailable'
                tiny['characters'] = len(body)
                if not tiny['retrieval_verified']:
                    raise RuntimeError('TinyFish returned no usable source content')
        except (ValueError, OSError, RuntimeError) as error:
            report['error'] = str(error)
        finally:
            peer.close()
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL); process.wait()
            process.stdin.close()
            process.stdout.close()
    return emit_report(report, args.output)


if __name__ == '__main__':
    raise SystemExit(main())
