import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from smoke import reader_content, source_urls


class SmokeContractTest(unittest.TestCase):
    def test_reader_accepts_text_json_and_sse_preserving_freshness_warning(self):
        data = {"url": "https://example.com/", "content": "real body", "warning": "cached snapshot"}
        for raw in [json.dumps({"data": data}), "event: data\ndata: " + json.dumps(data) + "\n\n"]:
            text = reader_content(raw, "https://example.com")
            self.assertIn("real body", text)
            self.assertIn("cached snapshot", text)
            self.assertEqual(source_urls(text), ["https://example.com/"])
        self.assertEqual(reader_content("plain text", "https://example.com"), "plain text")

    def test_code_example_urls_do_not_count_as_sources(self):
        text = "const server = 'https://localhost:1234';\nSource: https://react.dev/reference/react/useEffect"
        self.assertEqual(source_urls(text), ["https://react.dev/reference/react/useEffect"])

    def test_twenty_benchmark_questions_have_unique_ids_and_expectations(self):
        cases = json.loads((Path(__file__).resolve().parents[1] / "benchmarks/questions.json").read_text())
        self.assertEqual(len(cases), 20)
        self.assertEqual(len({c["id"] for c in cases}), 20)
        self.assertTrue(all(c["question"] and c["keywords"] for c in cases))
