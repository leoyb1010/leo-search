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

    def test_identical_text_across_urls_keeps_links_but_shares_group(self):
        result = self.run_ledger([{"url": "https://a.example/story", "content": "same report"},
                                  {"url": "https://b.example/story", "content": "same report"}])
        rows = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["evidence_group"], rows[1]["evidence_group"])
        self.assertEqual(rows[0]["independence"], "shared_provenance")

    def test_upstream_relationship_is_transitive(self):
        result = self.run_ledger([{"url": "https://a.example/", "upstream_source": "https://b.example/"},
                                  {"url": "https://b.example/", "upstream_source": "https://c.example/"},
                                  {"url": "https://c.example/"}])
        rows = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(len({r["evidence_group"] for r in rows}), 1)

    def test_duplicate_claims_and_conflicting_support_are_preserved(self):
        result = self.run_ledger([{"url": "https://a.example/", "claim_ids": ["c1"], "support": "supports"},
                                  {"url": "https://a.example/", "claim_ids": ["c2"], "support": "contradicts"}])
        row = json.loads(result.stdout)
        self.assertEqual(row["claim_ids"], ["c1", "c2"])
        self.assertEqual(row["support_values"], ["contradicts", "supports"])
        self.assertEqual(row["support"], "unknown")

    def test_unrelated_urls_do_not_claim_proven_independence(self):
        result = self.run_ledger([{"url": "https://a.example/"}, {"url": "https://b.example/"}])
        rows = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertNotEqual(rows[0]["evidence_group"], rows[1]["evidence_group"])
        self.assertTrue(all(r["independence"] == "unverified" for r in rows))

    def test_rejects_invalid_claim_contract(self):
        result = self.run_ledger([{"url": "https://a.example/", "claim_ids": "not-an-array"}])
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
