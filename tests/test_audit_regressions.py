"""Offline adversarial regressions; never read host credentials or call providers."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from request_budget import RequestBudget


class BudgetCancellationTest(unittest.TestCase):
    def test_interrupted_owner_resolves_singleflight_waiter(self):
        class Cancelled(BaseException):
            pass
        budget = RequestBudget(1)
        entered, finish = threading.Event(), threading.Event()
        errors = []
        def operation():
            entered.set()
            if not finish.wait(2):
                raise RuntimeError('fixture timed out')
            raise Cancelled('cancelled fixture')
        def invoke():
            try:
                budget.run('same', operation)
            except BaseException as error:
                errors.append(type(error))
        threads = [threading.Thread(target=invoke, daemon=True) for _ in range(2)]
        threads[0].start()
        self.assertTrue(entered.wait(2))
        threads[1].start()
        finish.set()
        for thread in threads:
            thread.join(2)
            self.assertFalse(thread.is_alive(), 'single-flight waiter was stranded')
        self.assertEqual(errors, [Cancelled, Cancelled])
        self.assertEqual((budget.calls, budget.cache_hits), (1, 1))

    def test_noninteger_limits_fail_before_any_operation(self):
        for limit in [True, False, 1.5, '2', 0, -1]:
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                RequestBudget(limit)


class EvidenceInputTest(unittest.TestCase):
    def ledger(self, records):
        return subprocess.run([sys.executable, str(ROOT/'scripts/evidence_ledger.py')],
            input=''.join(json.dumps(record)+'\n' for record in records),
            text=True, capture_output=True, timeout=5)

    def test_resource_identity_is_preserved(self):
        urls = ['https://example.com/article', 'https://example.com/article/',
                'https://example.com/article?id=1&id=2', 'https://example.com/article?id=2&id=1']
        result = self.ledger([{'url': url} for url in urls])
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual([row['canonical_url'] for row in rows], urls)

    def test_credentials_and_malformed_urls_rejected_without_leaking_input(self):
        urls = ['https://user:FAKE_PRIVATE_TOKEN@example.com/a', 'https://example.com:invalid/a',
                'https://example.com:99999/a', 'https://exa mple.com/a',
                'https://example.com/a\nFAKE_PRIVATE_TOKEN', 'file:///tmp/FAKE_PRIVATE_TOKEN',
                'https://example.com\\@evil.example/']
        for url in urls:
            with self.subTest(url=url):
                result = self.ledger([{'url': url}])
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, '')
                self.assertNotIn('FAKE_PRIVATE_TOKEN', result.stderr)

    def test_nontext_content_is_rejected(self):
        for content in [{}, [], 0, False]:
            with self.subTest(content=content):
                result = self.ledger([{'url': 'https://example.com', 'content': content}])
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, '')


class PortableInstallTest(unittest.TestCase):
    def run_installer(self, home, *args):
        return subprocess.run([sys.executable, str(ROOT/'scripts/install_portable.py'), *args],
            env={**os.environ, 'HOME': str(home)}, text=True, capture_output=True, timeout=5)

    def test_conflict_is_preserved_and_nonzero(self):
        with tempfile.TemporaryDirectory() as directory:
            home=Path(directory)
            target=home/'.agents/skills/leo-search'
            target.mkdir(parents=True)
            (target/'user-file').write_text('preserve me')
            result=self.run_installer(home, '--targets', 'agents')
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual((target/'user-file').read_text(), 'preserve me')
            self.assertFalse(target.is_symlink())

    def test_forced_backups_are_unique_and_repeated_target_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            home=Path(directory)
            target=home/'.agents/skills/leo-search'
            for content in ['first', 'second']:
                if target.is_symlink(): target.unlink()
                target.mkdir(parents=True)
                (target/'user-file').write_text(content)
                result=self.run_installer(home, '--targets', 'agents,agents', '--force')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(target.is_symlink())
            saved=sorted(p.read_text() for p in (home/'.leo-search-backups').rglob('user-file'))
            self.assertEqual(saved, ['first', 'second'])

    def test_empty_target_selection_is_error(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(self.run_installer(directory, '--targets', ',').returncode, 2)
