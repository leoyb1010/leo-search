"""Independent second role round: revoked hosts, spoofed sources and recovery."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import codex_probe
import install_portable
from test_native_rpc import peer_for
import test_role_round1 as round1


class RevokedAndSpoofedHost(unittest.TestCase):
    def test_legitimate_markdown_native_citation_remains_supported(self):
        status, report, _ = round1.NativeHostJourney().run_probe({'thread': {'id': 'synthetic'}},
            {'content': [{'type': 'text', 'text': '[Tools](https://modelcontextprotocol.io/docs/tools) ' + 'official tools ' * 10}]})
        self.assertEqual(status, 0)
        self.assertTrue(next(r for r in report['servers'] if r['name'].endswith('tinyfish'))['retrieval_verified'])

    def test_revoked_oauth_stops_before_thread_or_tool_even_with_cached_tools(self):
        output = io.StringIO()
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, 'config.toml').write_text('')
            process = MagicMock()
            process.poll.return_value = 0
            peer = MagicMock()
            peer.call.side_effect = [{}, round1.inventory()]
            def launch(*args, **kwargs):
                kwargs['stderr'].write('synthetic OAuth refresh invalid_grant')
                return process
            with patch.dict(os.environ, {'CODEX_HOME': directory}), \
                 patch.object(sys, 'argv', ['codex_probe', '--search']), \
                 patch.object(codex_probe.subprocess, 'Popen', side_effect=launch), \
                 patch.object(codex_probe, 'RpcPeer', return_value=peer), \
                 contextlib.redirect_stdout(output):
                status = codex_probe.main()
        report = json.loads(output.getvalue())
        self.assertEqual(status, 2)
        self.assertEqual(report['tool_calls'], 0)
        self.assertEqual(peer.call.call_count, 2)
        self.assertEqual(next(r for r in report['servers'] if r['name'].endswith('tinyfish'))['stage'], 'unavailable')

    def test_lookalike_or_body_only_domain_cannot_verify_tinyfish_source(self):
        journey = round1.NativeHostJourney()
        for body in ['Source: https://modelcontextprotocol.io.evil.example/\n',
                     'quoted modelcontextprotocol.io without a source field\n',
                     'Source: https://user:FAKE_PRIVATE_VALUE@modelcontextprotocol.io/\n']:
            with self.subTest(body=body):
                status, report, _ = journey.run_probe({'thread': {'id': 'synthetic'}},
                    {'content': [{'type': 'text', 'text': body + 'official tools ' * 10}]})
                self.assertEqual(status, 2)
                self.assertNotIn('FAKE_PRIVATE_VALUE', json.dumps(report))

    def test_native_boolean_reply_cannot_complete_integer_request(self):
        code = 'import sys,time;sys.stdin.readline();print(\'{"id":true,"result":{}}\',flush=True);time.sleep(10)'
        with peer_for(code) as peer:
            with self.assertRaisesRegex(RuntimeError, 'timed out'):
                peer.call(1, 'initialize', {})


class InstallerRecovery(unittest.TestCase):
    def test_post_backup_publish_failure_restores_existing_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            target = home / '.agents/skills/leo-search'
            target.mkdir(parents=True)
            (target / 'user-file').write_text('original')
            with patch.object(install_portable, 'TARGETS', {'agents': target}), \
                 patch.object(install_portable.Path, 'home', return_value=home), \
                 patch.object(sys, 'argv', ['install_portable', '--targets', 'agents', '--force']), \
                 patch.object(install_portable.os, 'replace', side_effect=OSError('publish failure')), \
                 contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(install_portable.main(), 1)
            self.assertFalse(target.is_symlink())
            self.assertEqual((target / 'user-file').read_text(), 'original')

    def test_failed_replacement_restores_original_target(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            target = home / '.agents/skills/leo-search'
            target.mkdir(parents=True)
            (target / 'user-file').write_text('original')
            with patch.object(install_portable, 'TARGETS', {'agents': target}), \
                 patch.object(install_portable.Path, 'home', return_value=home), \
                 patch.object(sys, 'argv', ['install_portable', '--targets', 'agents', '--force']), \
                 patch.object(install_portable.Path, 'symlink_to', side_effect=OSError('interrupted replacement')), \
                 contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(install_portable.main(), 1)
            self.assertFalse(target.is_symlink())
            self.assertEqual((target / 'user-file').read_text(), 'original')

    def test_concurrent_forced_installers_preserve_one_original(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            target = home / '.agents/skills/leo-search'
            target.mkdir(parents=True)
            (target / 'user-file').write_text('original')
            command = [sys.executable, str(Path(install_portable.__file__)), '--targets', 'agents', '--force']
            processes = [subprocess.Popen(command, env={**os.environ, 'HOME': directory},
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(6)]
            for process in processes:
                out, err = process.communicate(timeout=10)
                self.assertEqual(process.returncode, 0, out + err)
            self.assertTrue(target.is_symlink())
            self.assertEqual([p.read_text() for p in (home / '.leo-search-backups').rglob('user-file')], ['original'])
