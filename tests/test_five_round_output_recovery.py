"""Round 1: actual CLI operator output and recoverable filesystem boundaries."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import report_output
import codex_probe

class ReportRecoveryTests(unittest.TestCase):
    def test_interrupted_atomic_publish_preserves_original_and_cleans_stage(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'résultat.json'; path.write_text('old report')
            with patch.object(report_output.os,'replace',side_effect=OSError('fixture')):
                with self.assertRaises(OSError):report_output.write_report(path,'new report')
            self.assertEqual(path.read_text(),'old report')
            self.assertEqual(list(Path(root).iterdir()),[path])
            report_output.write_report(path,'新结果')
            self.assertEqual(path.read_text(encoding='utf-8'),'新结果')
    def test_symlink_output_is_rejected_without_overwriting_target(self):
        with tempfile.TemporaryDirectory() as root:
            actual=Path(root)/'original';actual.write_text('keep')
            link=Path(root)/'report';link.symlink_to(actual)
            with self.assertRaises(OSError):report_output.write_report(link,'new')
            self.assertTrue(link.is_symlink());self.assertEqual(actual.read_text(),'keep')
    def test_native_output_failure_keeps_complete_stdout_and_bounded_message(self):
        report={'servers':[], 'schema_version':1,'error':'synthetic unavailable'}
        with tempfile.TemporaryDirectory() as root:
            out,err=io.StringIO(),io.StringIO()
            with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
                self.assertEqual(codex_probe.emit_report(report,Path(root)),2)
            self.assertEqual(json.loads(out.getvalue()),report)
            self.assertNotIn('Traceback',err.getvalue())
            self.assertIn('stdout',err.getvalue())

    def test_first_write_empty_utf8_and_parent_file_are_recoverable(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'new'/'report.json'
            for content in ['', '非 ASCII ∞\n']:
                report_output.write_report(path,content)
                self.assertEqual(path.read_text(encoding='utf-8'),content)
            with self.assertRaises(OSError):report_output.write_report(path/'child','no')
            self.assertEqual(path.read_text(encoding='utf-8'),'非 ASCII ∞\n')
    def test_flush_failure_keeps_previous_report(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'report';path.write_text('old')
            with patch.object(report_output.os,'fsync',side_effect=OSError('fixture')):
                with self.assertRaises(OSError):report_output.write_report(path,'new')
            self.assertEqual(path.read_text(),'old')
            self.assertEqual(list(Path(root).iterdir()),[path])
