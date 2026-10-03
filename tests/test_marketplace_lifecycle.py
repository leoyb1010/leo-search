"""Actual filesystem/CLI install recovery with disposable HOME; never run real Codex."""
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import marketplace

class MarketplaceLifecycleTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.home = Path(self.temporary.name)
        self.path = self.home / 'marketplace.json'
    def tearDown(self):
        self.temporary.cleanup()
    def write(self, plugins):
        self.path.write_text(json.dumps({'name': 'personal', 'custom': {'keep': 42}, 'plugins': plugins}))
    def update(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return marketplace.update_marketplace(self.path)

    def test_repeated_updates_preserve_each_prior_state_and_unrelated_plugins(self):
        first = {'name': 'other-one', 'policy': {'custom': True}}
        second = {'name': 'other-two'}
        self.write([first]); self.update()
        self.write([second]); self.update()
        backups = list(self.home.glob('marketplace.json.bak.*'))
        self.assertEqual(len(backups), 2)
        self.assertEqual({json.loads(p.read_text())['plugins'][0]['name'] for p in backups}, {'other-one', 'other-two'})
        data = json.loads(self.path.read_text())
        self.assertEqual(data['plugins'][0], second); self.assertEqual(data['custom'], {'keep': 42})

    def test_six_concurrent_installers_preserve_original_once(self):
        self.write([{'name': 'untouched'}])
        processes = [subprocess.Popen([sys.executable, str(ROOT / 'scripts/marketplace.py'), str(self.path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(6)]
        for p in processes:
            stdout, stderr = p.communicate(timeout=10)
            self.assertEqual(p.returncode, 0, (stdout, stderr))
        data = json.loads(self.path.read_text())
        self.assertEqual([p['name'] for p in data['plugins']], ['untouched', 'leo-search'])
        self.assertEqual(len(list(self.home.glob('marketplace.json.bak.*'))), 1)

    def test_publish_failure_leaves_original_and_unique_backup(self):
        self.write([{'name': 'original'}]); before = self.path.read_bytes()
        with patch.object(marketplace.os, 'replace', side_effect=OSError('synthetic publish failure')):
            with self.assertRaises(OSError): self.update()
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual([p.read_bytes() for p in self.home.glob('marketplace.json.bak.*')], [before])
        self.assertEqual(list(self.home.glob('marketplace.*.json')), [])
        self.update(); self.assertIn('leo-search', self.path.read_text())

    def test_invalid_shapes_fail_before_backup_or_mutation(self):
        for value in [[], 42, {'plugins': {}}, {'plugins': [None]}, {'plugins': [{'title': 'bad'}]}, {'name': None, 'plugins': []}]:
            with self.subTest(value=value):
                self.path.write_text(json.dumps(value)); before = self.path.read_bytes()
                with self.assertRaises(ValueError): self.update()
                self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(self.home.glob('marketplace.json.bak.*')), [])

    def test_duplicate_leo_entries_converge_without_reordering_other_entries(self):
        self.write([{'name': 'first'}, {'name': 'leo-search', 'obsolete': 1}, {'name': 'second'}, {'name': 'leo-search', 'obsolete': 2}])
        self.update(); once = self.path.read_bytes(); self.update()
        self.assertEqual(self.path.read_bytes(), once)
        self.assertEqual([p['name'] for p in json.loads(once)['plugins']], ['first', 'leo-search', 'second'])
        self.assertEqual(len(list(self.home.glob('marketplace.json.bak.*'))), 1)

    def test_cli_invalid_json_has_bounded_diagnostic_without_echoing_content(self):
        self.path.write_text('SYNTHETIC_PRIVATE_MARKER')
        p = subprocess.run([sys.executable, str(ROOT / 'scripts/marketplace.py'), str(self.path)], text=True, capture_output=True)
        self.assertEqual(p.returncode, 1)
        self.assertNotIn('SYNTHETIC_PRIVATE_MARKER', p.stdout + p.stderr)
        self.assertNotIn('Traceback', p.stderr)
        self.assertEqual(self.path.read_text(), 'SYNTHETIC_PRIVATE_MARKER')

    def test_shell_install_failure_and_retry_use_the_safe_updater(self):
        plugin = self.home / 'plugins/leo-search'
        shutil.copytree(ROOT / 'scripts', plugin / 'scripts')
        doctor = plugin / 'scripts/doctor.sh'; doctor.write_text('#!/bin/sh\nexit 2\n'); doctor.chmod(0o755)
        binary = self.home / 'bin'; binary.mkdir()
        codex = binary / 'codex'; codex.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$HOME/codex-calls"\nexit "${FAKE_CODEX_EXIT:-0}"\n'); codex.chmod(0o755)
        target = self.home / '.agents/plugins/marketplace.json'; target.parent.mkdir(parents=True)
        target.write_text(json.dumps({'name': 'personal', 'plugins': [{'name': 'keep-me'}]}))
        env = {**os.environ, 'HOME': str(self.home), 'PATH': str(binary) + os.pathsep + os.environ['PATH'], 'FAKE_CODEX_EXIT': '23'}
        failed = subprocess.run(['sh', str(plugin / 'scripts/install.sh')], env=env, text=True, capture_output=True)
        self.assertEqual(failed.returncode, 23); self.assertNotIn('Leo Search installed.', failed.stdout)
        env['FAKE_CODEX_EXIT'] = '0'
        retry = subprocess.run(['sh', str(plugin / 'scripts/install.sh')], env=env, text=True, capture_output=True)
        self.assertEqual(retry.returncode, 0, retry.stderr)
        self.assertIn('optional-route warnings', retry.stdout)
        self.assertEqual([p['name'] for p in json.loads(target.read_text())['plugins']], ['keep-me', 'leo-search'])
        self.assertEqual((self.home / 'codex-calls').read_text().splitlines(), ['plugin add leo-search@personal'] * 2)

if __name__ == '__main__': unittest.main()
