"""Test native protocol framing with disposable child processes, no Codex launch."""
import contextlib
import subprocess
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from codex_probe import RpcPeer, isolated_args


@contextlib.contextmanager
def peer_for(code):
    process=subprocess.Popen([sys.executable,'-c',code], stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0)
    peer=RpcPeer(process, timeout=0.3, overall_timeout=1)
    try:
        yield peer
    finally:
        peer.close()
        process.kill()
        process.wait(timeout=2)
        process.stdin.close()
        process.stdout.close()


class NativeRpcTest(unittest.TestCase):
    def test_inline_nested_and_dotted_config_tables_are_isolated(self):
        for config in ['plugins = { "other@personal" = {enabled=true}}',
                       '[plugins."other@personal".mcp_servers.foo]\nenabled=true']:
            self.assertIn('plugins."other@personal".enabled=false',isolated_args(config))
        self.assertIn('mcp_servers."server.with.dot".enabled=false',
            isolated_args('[mcp_servers."server.with.dot"]\ncommand="fixture"'))

    def test_partial_frame_obeys_deadline(self):
        with peer_for('import sys,time;sys.stdin.readline();sys.stdout.write("{");sys.stdout.flush();time.sleep(10)') as peer:
            started=time.monotonic()
            with self.assertRaisesRegex(RuntimeError,'timed out'):
                peer.call(1,'initialize',{})
            self.assertLess(time.monotonic()-started,1.5)

    def test_multiple_frames_in_one_pipe_read_are_not_lost(self):
        code='import sys,time;sys.stdin.readline();print(\'{"method":"notification"}\\n{"id":1,"result":{"ok":true}}\',flush=True);time.sleep(10)'
        with peer_for(code) as peer:
            self.assertEqual(peer.call(1,'initialize',{}),{'ok':True})

    def test_malformed_and_interactive_frames_fail_closed(self):
        for frame in ['[]','not JSON','{"id":1,"method":"approval","params":{}}',
                      '{"id":1,"error":{"message":"FAKE_PRIVATE_VALUE"}}']:
            with self.subTest(frame=frame), peer_for('import sys,time;sys.stdin.readline();print('+repr(frame)+',flush=True);time.sleep(10)') as peer:
                with self.assertRaises(RuntimeError) as error:
                    peer.call(1,'initialize',{})
                self.assertNotIn('FAKE_PRIVATE_VALUE',str(error.exception))
