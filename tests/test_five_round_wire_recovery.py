"""Round 2: every role still works when one imported/provider payload is malformed."""
import json, os, subprocess, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import protocol_check, smoke
class WireRecoveryTests(unittest.TestCase):
 def cli(self,name,data,*args):
  return subprocess.run([sys.executable,str(ROOT/'scripts'/name),*map(str,args)],input=data,text=True,capture_output=True,timeout=5)
 def test_deep_protocol_frame_becomes_invalid_not_unhandled_recursion(self):
  raw='['*2000+'0'+']'*2000
  self.assertFalse(protocol_check.valid_initialize(raw))
  case={'id':'fixture','route':'jina','question':'fixture','url':'https://example.com','keywords':['fixture']}
  with patch.object(smoke,'http',return_value=raw):
   self.assertEqual(smoke.probe(case)['status'],'unavailable')
 def test_bad_unicode_or_nonfinite_metadata_rejects_whole_ledger_cleanly(self):
  good=json.dumps({'url':'https://example.com/good','title':'正常'})
  for value in ['{"url":"https://example.com","title":"\\ud800"}','{"url":"https://example.com","score":NaN}','{"url":"https://example.com","score":Infinity}', '{"url":"https://example.com","score":1e400}', '{"url":"https://example.com","score":-1e400}', '{"url":"https://example.com","meta":'+'['*2000+'0'+']'*2000+'}']:
   with self.subTest(value=value[:70]):
    p=self.cli('evidence_ledger.py',good+'\n'+value)
    self.assertEqual(p.returncode,2);self.assertEqual(p.stdout,'');self.assertNotIn('Traceback',p.stderr)
 def test_deep_corrupt_marketplace_is_preserved_with_actionable_exit(self):
  with tempfile.TemporaryDirectory() as root:
   p=Path(root)/'marketplace.json';original='{"plugins":'+'['*2000+'0'+']'*2000+'}';p.write_text(original)
   result=self.cli('marketplace.py','',p)
   self.assertEqual(result.returncode,1);self.assertNotIn('Traceback',result.stderr)
   self.assertEqual(p.read_text(),original);self.assertFalse(list(Path(root).glob('*.bak.*')))

 def test_finite_numeric_unicode_and_depth_boundaries(self):
  for raw,expected in [('1e308',1e308),('-1e308',-1e308),('-0.0',-0.0),('42',42),('"中文 🌊"','中文 🌊')]:
   self.assertEqual(protocol_check.load_json(raw),expected)
  self.assertEqual(protocol_check.load_json('-0.0').hex(),(-0.0).hex())
  protocol_check.load_json('['*64+'0'+']'*64)
  with self.assertRaises(ValueError):protocol_check.load_json('['*65+'0'+']'*65)
  for raw in ['1e400','-1e400','NaN','Infinity','-Infinity']:
   with self.assertRaises(ValueError):protocol_check.load_json(raw)
 def test_overflow_is_rejected_at_every_shared_input_contract(self):
  raw='{"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2025-11-25","serverInfo":{"name":"fixture"},"metadata":{"score":1e400}}}'
  self.assertFalse(protocol_check.valid_initialize(raw))
  raw='{"resource":"https://agent.tinyfish.ai/mcp","authorization_servers":["https://example.com"],"score":1e400}'
  self.assertFalse(protocol_check.valid_oauth_metadata(raw))
  case={'id':'fixture','route':'jina','question':'fixture','url':'https://example.com','keywords':['fixture']}
  raw='{"url":"https://example.com","content":"fixture","score":1e400}'
  with patch.object(smoke,'http',return_value=raw):self.assertEqual(smoke.probe(case)['status'],'unavailable')
  from test_native_rpc import peer_for
  native='import sys;sys.stdin.readline();print(\'{"id":1,"result":{"score":1e400}}\',flush=True)'
  with peer_for(native) as peer:
   with self.assertRaisesRegex(RuntimeError,'invalid native RPC frame'):peer.call(1,'initialize',{})
  with tempfile.TemporaryDirectory() as root:
   path=Path(root)/'marketplace.json';original='{"plugins":[],"score":1e400}';path.write_text(original)
   result=self.cli('marketplace.py','',path)
   self.assertEqual(result.returncode,1);self.assertEqual(path.read_text(),original);self.assertNotIn('Traceback',result.stderr)
