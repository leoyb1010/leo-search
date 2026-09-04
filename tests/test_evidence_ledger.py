import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "evidence_ledger.py"


class EvidenceLedgerTest(unittest.TestCase):
    def run_ledger(self, records: list[dict[str, object]]) -> subprocess.CompletedProcess[str]:
        payload = "".join(json.dumps(record) + "\n" for record in records)
        return subprocess.run(
            [sys.executable, str(SCRIPT)],
            input=payload,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_normalizes_and_deduplicates_urls(self) -> None:
        result = self.run_ledger(
            [
                {"url": "HTTPS://Example.com/story/?utm_source=x&id=7#top", "title": "First"},
                {"url": "https://example.com/story?id=7", "title": "Duplicate"},
            ]
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        records = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["canonical_url"], "https://example.com/story?id=7")
        self.assertEqual(records[0]["duplicate_count"], 2)

    def test_keeps_distinct_content_for_same_url(self) -> None:
        result = self.run_ledger(
            [
                {"url": "https://example.com/live", "content": "version one"},
                {"url": "https://example.com/live", "content": "version two"},
            ]
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        records = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(len(records), 2)
        self.assertNotEqual(records[0]["content_hash"], records[1]["content_hash"])

    def test_rejects_record_without_url(self) -> None:
        result = self.run_ledger([{"title": "missing"}])
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
