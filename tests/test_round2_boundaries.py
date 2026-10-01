import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import codex_probe
import smoke
from evidence_ledger import canonical_url


class RoundTwoBoundaries(unittest.TestCase):
    def test_query_octets_flags_and_empty_delimiter_preserve_identity(self):
        urls=['https://example.com/?q=%FF','https://example.com/?q=%FE',
              'https://example.com/?flag','https://example.com/?flag=',
              'https://example.com/?','https://example.com/',
              'https://example.com/?q=%20','https://example.com/?q=+']
        self.assertEqual([canonical_url(url) for url in urls],urls)
        self.assertEqual(canonical_url('https://example.com/?q=%FF&utm_source=x&flag'),
                         'https://example.com/?q=%FF&flag')

    def test_invalid_native_inventory_is_bounded_and_redacted(self):
        for rows in [[{}],[None],[{'name':'leo-search-exa','tools':None}]]:
            with self.subTest(rows=rows),self.assertRaises(RuntimeError):
                codex_probe.summarize(rows)

    def test_missing_native_executable_produces_report_not_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory,'config.toml').write_text('')
            output=io.StringIO()
            with patch.dict(os.environ,{'CODEX_HOME':directory}),patch.object(sys,'argv',['codex_probe']), \
                 patch.object(codex_probe.subprocess,'Popen',side_effect=FileNotFoundError('FAKE_SECRET')),contextlib.redirect_stdout(output):
                self.assertEqual(codex_probe.main(),2)
            result=json.loads(output.getvalue())
            self.assertIn('Could not start native server',result['error'])
            self.assertNotIn('FAKE_SECRET',output.getvalue())

    def test_malformed_provider_rows_become_unavailable_instead_of_crashing_pool(self):
        case={'id':'fixture','route':'exa','question':'synthetic','keywords':['synthetic']}
        for raw in ['[]','{"result":null}',
                    '{"jsonrpc":"2.0","id":1,"result":{"tools":[null]}}',
                    '{"jsonrpc":"9.9","id":999,"result":{"tools":[]}}',
                    '{"jsonrpc":"2.0","id":1,"result":{"tools":null}}']:
            with self.subTest(raw=raw),patch.object(smoke,'http',return_value=raw):
                result=smoke.probe(case)
                self.assertEqual(result['status'],'unavailable')
                self.assertIn('reason',result)

    def test_tool_content_and_reader_shapes_rejected_without_payload_echo(self):
        for content in [None,[None],[{'type':'text','text':None}]]:
            with self.subTest(content=content),self.assertRaises(RuntimeError):
                smoke.text_content({'content':content})
        with self.assertRaises(RuntimeError):smoke.reader_content('[]','https://example.com')
