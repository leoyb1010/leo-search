"""New role round 1: operator, host controller, provider and evidence consumer.

Every server/process response is synthetic; no host configuration or network is read.
"""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import codex_probe
import protocol_check
import smoke


def inventory():
    return {'data': [{'name': 'leo-search-' + name, 'tools': {'search': {}}}
                     for name in ('exa', 'context7', 'tinyfish')]}


class NativeHostJourney(unittest.TestCase):
    def run_probe(self, thread, result):
        output = io.StringIO()
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, 'config.toml').write_text('')
            process = MagicMock()
            process.poll.return_value = 0
            peer = MagicMock()
            peer.call.side_effect = [{}, inventory(), thread, result]
            with patch.dict(os.environ, {'CODEX_HOME': directory}), \
                 patch.object(sys, 'argv', ['codex_probe', '--search']), \
                 patch.object(codex_probe.subprocess, 'Popen', return_value=process), \
                 patch.object(codex_probe, 'RpcPeer', return_value=peer), \
                 contextlib.redirect_stdout(output):
                status = codex_probe.main()
            self.assertTrue(peer.close.called)
            self.assertTrue(process.stdin.close.called)
        return status, json.loads(output.getvalue()), peer

    def test_authorized_native_host_one_call_happy_path(self):
        status, report, peer = self.run_probe({'thread': {'id': 'synthetic-thread'}},
            {'content': [{'type': 'text', 'text': 'Source: https://modelcontextprotocol.io/ ' + 'official tools ' * 10}]})
        self.assertEqual(status, 0)
        self.assertEqual(report['tool_calls'], 1)
        self.assertEqual(peer.call.call_count, 4)

    def test_malformed_thread_handoff_stops_before_provider_call(self):
        for thread in [None, {}, {'thread': None}, {'thread': {}}, {'thread': {'id': None}}]:
            with self.subTest(thread=thread):
                status, report, peer = self.run_probe(thread, {})
                self.assertEqual(status, 2)
                self.assertEqual(report['tool_calls'], 0)
                self.assertEqual(peer.call.call_count, 3)

    def test_malformed_provider_tool_result_is_redacted_report(self):
        for result in [None, [], {'content': None}, {'content': [None]},
                       {'content': [{'type': 'text', 'text': {'secret': 'FAKE_PRIVATE_VALUE'}}]}]:
            with self.subTest(result=result):
                status, report, _ = self.run_probe({'thread': {'id': 'synthetic-thread'}}, result)
                self.assertEqual(status, 2)
                self.assertNotIn('FAKE_PRIVATE_VALUE', json.dumps(report))


class ProviderEvidenceJourney(unittest.TestCase):
    def test_boolean_response_id_cannot_impersonate_numeric_request(self):
        raw = json.dumps({'jsonrpc': '2.0', 'id': True, 'result': {
            'protocolVersion': '2025-03-26', 'serverInfo': {'name': 'synthetic-provider'}}})
        self.assertFalse(protocol_check.valid_initialize(raw))
        with patch.object(smoke, 'http', return_value=raw):
            with self.assertRaises(RuntimeError):
                smoke.rpc('exa', 'initialize', {})

    def test_missing_reader_provenance_is_not_fabricated_from_request(self):
        with self.assertRaises(RuntimeError):
            smoke.reader_content(json.dumps({'data': {'content': 'body'}}), 'https://example.com/request')

    def test_credential_bearing_source_is_not_published(self):
        case = {'id': 'fixture', 'route': 'jina', 'url': 'https://example.com/',
                'question': 'synthetic', 'keywords': ['synthetic']}
        payload = 'URL Source: https://user:FAKE_PRIVATE_VALUE@example.com/\nMarkdown Content:\n' + 'synthetic ' * 20
        with patch.object(smoke, 'http', return_value=payload):
            row = smoke.probe(case)
        self.assertEqual(row['status'], 'unavailable')
        self.assertNotIn('FAKE_PRIVATE_VALUE', json.dumps(row))

    def test_reader_mismatched_source_does_not_satisfy_requested_resource(self):
        case = {'id': 'fixture', 'route': 'jina', 'url': 'https://example.com/request',
                'question': 'synthetic', 'keywords': ['synthetic']}
        with patch.object(smoke, 'http', return_value='URL Source: https://different.example/\nMarkdown Content:\n' + 'synthetic ' * 20):
            row = smoke.probe(case)
        self.assertEqual(row['status'], 'fail')
        self.assertFalse(row['checks']['source_matches_requested'])
