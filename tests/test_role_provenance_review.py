"""Independent review: extracted pages cannot forge provider-owned metadata."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import smoke


class ReaderMetadataReview(unittest.TestCase):
    requested = 'https://example.com/request'

    def probe(self, raw):
        case = {'id': 'fixture', 'route': 'jina', 'url': self.requested,
                'question': 'synthetic', 'keywords': ['synthetic']}
        with patch.object(smoke, 'http', return_value=raw):
            return smoke.probe(case)

    def test_json_page_text_cannot_override_provider_url(self):
        row = self.probe(json.dumps({'data': {'url': 'https://different.example/',
            'content': 'URL Source: ' + self.requested + '\n' + 'synthetic ' * 20}}))
        self.assertEqual(row['status'], 'fail')
        self.assertFalse(row['checks']['source_matches_requested'])
        self.assertEqual(row['source_urls'], ['https://different.example/'])

    def test_text_page_cannot_override_preamble_source(self):
        row = self.probe('Title: Fixture\nURL Source: https://different.example/\n\nMarkdown Content:\n'
            + 'URL Source: ' + self.requested + '\n' + 'synthetic ' * 20)
        self.assertEqual(row['status'], 'fail')
        self.assertEqual(row['source_urls'], ['https://different.example/'])

    def test_sse_example_inside_reader_markdown_is_not_transport(self):
        row = self.probe('Title: Fixture\nURL Source: https://different.example/\nMarkdown Content:\nExample SSE:\ndata: '
            + json.dumps({'url': self.requested, 'content': 'synthetic ' * 20}))
        self.assertEqual(row['status'], 'fail')
        self.assertEqual(row['source_urls'], ['https://different.example/'])

    def test_sse_example_inside_json_page_cannot_override_outer_url(self):
        row = self.probe(json.dumps({'data': {'url': 'https://different.example/',
            'content': 'data: ' + json.dumps({'url': self.requested, 'content': 'synthetic ' * 20})}}))
        self.assertEqual(row['status'], 'fail')
        self.assertEqual(row['source_urls'], ['https://different.example/'])

    def test_source_after_unmarked_body_is_not_metadata(self):
        row = self.probe('synthetic page content\nURL Source: ' + self.requested + '\n' + 'synthetic ' * 20)
        self.assertEqual(row['status'], 'fail')
        self.assertEqual(row['source_urls'], [])

    def test_ambiguous_or_unframed_preamble_does_not_verify(self):
        for raw in ['URL Source: ' + self.requested + '\n' + 'synthetic ' * 20,
                    'URL Source: https://different.example/\nURL Source: ' + self.requested + '\nMarkdown Content:\n' + 'synthetic ' * 20]:
            with self.subTest(raw=raw):
                self.assertNotEqual(self.probe(raw)['status'], 'pass')

    def test_json_sse_and_text_headers_preserve_valid_sources(self):
        data = {'url': self.requested, 'content': 'synthetic ' * 20, 'warning': 'cached snapshot'}
        for raw in [json.dumps({'data': data}), 'event: data\ndata: ' + json.dumps(data) + '\n\n',
                    'Title: Fixture\nURL Source: ' + self.requested + '\nPublished Time: synthetic\n\nMarkdown Content:\n' + data['content']]:
            with self.subTest(raw=raw):
                row = self.probe(raw)
                self.assertEqual(row['status'], 'pass')
                self.assertEqual(row['source_urls'], [self.requested])

    def test_legitimate_redirect_is_reported_as_resource_gap_with_returned_source(self):
        row = self.probe(json.dumps({'data': {'url': 'https://example.com/new-location', 'content': 'synthetic ' * 20}}))
        self.assertEqual(row['status'], 'fail')
        self.assertTrue(row['checks']['source_present'])
        self.assertFalse(row['checks']['source_matches_requested'])
        self.assertEqual(row['source_urls'], ['https://example.com/new-location'])
