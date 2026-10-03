"""Product transport compatibility; all responses are synthetic and offline."""
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import protocol_check
import smoke

class ProductProtocolTest(unittest.TestCase):
    reply = {'jsonrpc': '2.0', 'id': 1, 'result': {'protocolVersion': '2025-06-18', 'serverInfo': {'name': 'fixture'}}}

    def test_all_sse_line_endings_and_leading_bom(self):
        for newline in ['\n', '\r\n', '\r']:
            for bom in ['', '\ufeff']:
                with self.subTest(newline=newline, bom=bom):
                    raw = bom + newline.join([': keepalive', 'event: message', 'data: ' + json.dumps(self.reply), '', ''])
                    self.assertTrue(protocol_check.valid_initialize(raw))
                    with patch.object(smoke, 'http', return_value=raw):
                        self.assertEqual(smoke.rpc('exa', 'initialize', {}), self.reply['result'])

    def test_duplicate_reply_id_cannot_mask_an_earlier_error(self):
        bad = {'jsonrpc': '2.0', 'id': 1, 'error': {'code': -32000, 'message': 'synthetic'}}
        for frames in [[bad, self.reply], [self.reply, self.reply], [self.reply, bad]]:
            with self.subTest(frames=frames):
                raw = ''.join('data: ' + json.dumps(frame) + '\n\n' for frame in frames)
                self.assertFalse(protocol_check.valid_initialize(raw))
                with patch.object(smoke, 'http', return_value=raw), self.assertRaises(RuntimeError):
                    smoke.rpc('exa', 'initialize', {})

    def test_unrelated_notifications_do_not_make_the_one_reply_ambiguous(self):
        raw = 'data: ' + json.dumps({'jsonrpc': '2.0', 'method': 'notifications/progress', 'params': {}}) + '\n\n'
        raw += 'data: ' + json.dumps(self.reply) + '\n\n'
        self.assertTrue(protocol_check.valid_initialize(raw))

    def test_reader_cr_sse_keeps_authoritative_outer_provenance(self):
        requested = 'https://example.com/request'
        source = 'https://example.com/actual'
        data = {'url': source, 'content': 'URL Source: ' + requested + '\n' + 'synthetic ' * 20}
        case = {'id': 'fixture', 'route': 'jina', 'url': requested, 'question': 'synthetic', 'keywords': ['synthetic']}
        raw = '\ufeffevent: message\rdata: ' + json.dumps(data) + '\r\r'
        with patch.object(smoke, 'http', return_value=raw):
            row = smoke.probe(case)
        self.assertEqual(row['status'], 'fail')
        self.assertEqual(row['source_urls'], [source])
        self.assertFalse(row['checks']['source_matches_requested'])

    def test_reader_text_bom_does_not_turn_body_examples_into_provenance(self):
        source = 'https://example.com/actual'
        content, urls = smoke.reader_document('\ufeffTitle: Fixture\nURL Source: ' + source
            + '\nMarkdown Content:\nURL Source: https://forged.example/\n' + 'synthetic ' * 20, source)
        self.assertEqual(urls, [source])
        self.assertIn('https://forged.example/', content)

    def test_cli_cr_sse_has_machine_readable_exit_without_provider_content(self):
        raw = 'data: ' + json.dumps(self.reply) + '\r\r'
        result = subprocess.run([sys.executable, 'scripts/protocol_check.py', 'initialize'], input=raw, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '')
        self.assertEqual(result.stderr, '')
