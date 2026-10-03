"""Round 4: ambiguous duplicate fields must not rewrite evidence or operator data."""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import protocol_check, smoke
class AmbiguousDataTests(unittest.TestCase):
 def test_duplicate_field_and_escaped_key_collision_rejected(self):
  for raw in ['{"id":999,"id":1}','{"a":1,"\\u0061":2}','{"meta":{"score":1,"score":2}}']:
   with self.assertRaisesRegex(ValueError,'duplicate fields'):protocol_check.load_json(raw)
  self.assertEqual(protocol_check.load_json('{"rows":[{"id":1},{"id":2}]}'),{'rows':[{'id':1},{'id':2}]})
 def test_initialize_reader_native_reject_ambiguous_sources_or_identity(self):
  self.assertFalse(protocol_check.valid_initialize('{"jsonrpc":"2.0","id":999,"id":1,"result":{"protocolVersion":"fixture","serverInfo":{"name":"fixture"}}}'))
  raw='{"url":"https://wrong.example","url":"https://example.com","content":"fixture"}'
  with patch.object(smoke,'http',return_value=raw):
   self.assertEqual(smoke.probe({'id':'fixture','route':'jina','url':'https://example.com','question':'fixture','keywords':['fixture']})['status'],'unavailable')
  from test_native_rpc import peer_for
  with peer_for('import sys;sys.stdin.readline();print(\'{"id":999,"id":1,"result":{}}\',flush=True)') as peer:
   with self.assertRaisesRegex(RuntimeError,'invalid native RPC frame'):peer.call(1,'initialize',{})
 def test_analyst_batch_and_marketplace_original_are_preserved(self):
  good=json.dumps({'url':'https://example.com/good','content':'synthetic'})
  bad='{"url":"https://wrong.example","url":"https://example.com","content":"synthetic"}'
  r=subprocess.run([sys.executable,str(ROOT/'scripts/evidence_ledger.py')],input=good+'\n'+bad,text=True,capture_output=True,timeout=5)
  self.assertEqual(r.returncode,2);self.assertEqual(r.stdout,'');self.assertNotIn('Traceback',r.stderr)
  with tempfile.TemporaryDirectory() as root:
   path=Path(root)/'marketplace.json';original='{"name":"personal","plugins":[{"name":"keep-me"}],"plugins":[]}'
   path.write_text(original)
   r=subprocess.run([sys.executable,str(ROOT/'scripts/marketplace.py'),str(path)],text=True,capture_output=True,timeout=5)
   self.assertEqual(r.returncode,1);self.assertEqual(path.read_text(),original);self.assertFalse(list(Path(root).glob('*.bak.*')))
 def test_genuine_local_git_worktree_is_accepted_with_network_mutations_stubbed(self):
  git=shutil.which('git');self.assertIsNotNone(git)
  with tempfile.TemporaryDirectory() as root:
   home=Path(root);source=home/'source';source.mkdir();work=home/'plugins/leo-search';work.parent.mkdir()
   def run(*args):subprocess.run([git,*args],check=True,capture_output=True,text=True,env={**os.environ,'HOME':root})
   run('init',str(source));(source/'README').write_text('synthetic worktree fixture')
   run('-C',str(source),'add','README');run('-C',str(source),'-c','user.name=Fixture','-c','user.email=fixture@example.test','commit','-m','fixture')
   run('-C',str(source),'worktree','add','-b','fixture-audit',str(work));self.assertTrue((work/'.git').is_file())
   scripts=work/'scripts';scripts.mkdir();shutil.copy2(ROOT/'scripts/update.sh',scripts/'update.sh')
   install=scripts/'install.sh';install.write_text('#!/bin/sh\necho synthetic >> "$HOME/install-calls"\n');install.chmod(0o755)
   binary=home/'bin';binary.mkdir();proxy=binary/'git'
   proxy.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$HOME/git-calls"\ncase "$*" in\n *"rev-parse --is-inside-work-tree"*) exec '+git+' "$@" ;;\n *"remote get-url origin"*) echo https://github.com/leoyb1010/leo-search.git ;;\n *"pull --ff-only"*) exit 0 ;;\n *) exit 77 ;;\nesac\n');proxy.chmod(0o755)
   env={**os.environ,'HOME':root,'PATH':str(binary)+os.pathsep+os.environ['PATH']}
   for script in [scripts/'update.sh',ROOT/'scripts/bootstrap.sh']:
    r=subprocess.run(['sh',str(script)],env=env,capture_output=True,text=True,timeout=5);self.assertEqual(r.returncode,0,r.stderr)
   self.assertEqual((home/'install-calls').read_text().splitlines(),['synthetic','synthetic'])
   self.assertEqual((home/'git-calls').read_text().count('pull --ff-only'),2)
