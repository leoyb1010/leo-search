"""Real CLI processes, synthetic providers, disposable HOME. No live network/Codex."""
import json, os, subprocess, sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CURL=r'''#!/usr/bin/env python3
import json,os,sys
args=sys.argv[1:];mode=os.environ.get('FIXTURE_MODE','normal');url=args[-1]
if mode=='malformed':print('not-json\n200',end='');raise SystemExit()
if mode=='offline':print('SYNTHETIC_PRIVATE\n503',end='');raise SystemExit(22)
body='MCP useEffect cleanup Path transaction git motion focus ownership Swift Vue json release computed loading domain documentation. '+'Synthetic source prose. '*6
if '--data-binary' not in args:
 print('Title: Fixture\nURL Source: '+url.removeprefix('https://r.jina.ai/')+'\nMarkdown Content:\n'+body+'\n200',end='');raise SystemExit()
p=json.loads(args[args.index('--data-binary')+1])
if p['method']=='tools/list':
 names=['web_search_exa'] if 'exa' in url else ['resolve-library-id','query-docs'];result={'tools':[{'name':n} for n in names]}
elif p['params']['name']=='resolve-library-id':result={'content':[{'type':'text','text':'Context7-compatible library ID: /fixture/docs'}]}
else:result={'content':[{'type':'text','text':'Source: https://example.com/official\n'+body}]}
print(json.dumps({'jsonrpc':'2.0','id':1,'result':result})+'\n200',end='')
'''
CODEX=r'''#!/usr/bin/env python3
import json,sys
for line in sys.stdin:
 p=json.loads(line)
 if 'id' not in p:continue
 method=p['method']
 if method=='mcpServerStatus/list':r={'data':[{'name':'leo-search-'+n,'tools':{'search':{}},'authStatus':'authenticated'} for n in ['exa','context7','tinyfish']]}
 elif method=='thread/start':r={'thread':{'id':'synthetic-ephemeral'}}
 elif method=='mcpServer/tool/call':r={'content':[{'type':'text','text':'Source: https://modelcontextprotocol.io/docs/tools\n'+'Synthetic Model Context Protocol tools specification. '*5}]}
 else:r={}
 print(json.dumps({'id':p['id'],'result':r}),flush=True)
'''
class FullCliJourneys(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.home=Path(self.temp.name);self.bin=self.home/'bin';self.bin.mkdir()
  for name,body in [('curl',CURL),('codex',CODEX)]:
   f=self.bin/name;f.write_text(body);f.chmod(0o755)
  config=self.home/'codex';config.mkdir();(config/'config.toml').write_text('[plugins."unrelated@personal"]\nenabled=true\n')
  self.env={**os.environ,'HOME':str(self.home),'CODEX_HOME':str(config),'PATH':str(self.bin)+os.pathsep+os.environ['PATH'],'LEO_SEARCH_PROXY':'','LEO_SEARCH_PROXY_FILE':str(self.home/'absent')}
 def tearDown(self):self.temp.cleanup()
 def run_cli(self,script,*args,mode='normal',data=None):
  return subprocess.run([sys.executable,str(ROOT/'scripts'/script),*map(str,args)],env={**self.env,'FIXTURE_MODE':mode},input=data,text=True,capture_output=True,timeout=15)
 def test_fast_scoped_deep_fallback_research_and_persistent_report(self):
  for args,total in [((),3),(('--case','exa-01'),1),(('--benchmark','--max-requests','28'),20),(('--case','exa-03','--fallback-only','--max-requests','2'),1)]:
   with self.subTest(args=args):
    output=self.home/'reports'/'结果.json';p=self.run_cli('smoke.py',*args,'--output',output)
    self.assertEqual(p.returncode,0,p.stderr);r=json.loads(p.stdout)
    self.assertEqual(r,json.loads(output.read_text()));self.assertEqual(r['passed'],total)
    self.assertLessEqual(r['requests']['used'],r['requests']['limit']);self.assertEqual(r['semantic_accuracy'],'not_scored')
 def test_budget_partial_results_invalid_input_error_and_retry(self):
  p=self.run_cli('smoke.py','--benchmark','--max-requests','1');r=json.loads(p.stdout)
  self.assertEqual(p.returncode,2);self.assertEqual(r['requests']['used'],1);self.assertEqual(r['total'],20)
  for mode in ['malformed','offline']:
   p=self.run_cli('smoke.py','--case','exa-01',mode=mode)
   self.assertEqual(p.returncode,2);self.assertNotIn('SYNTHETIC_PRIVATE',p.stdout+p.stderr);self.assertNotIn('Traceback',p.stderr)
   self.assertEqual(json.loads(p.stdout)['cases'][0]['status'],'unavailable')
  self.assertEqual(self.run_cli('smoke.py','--case','exa-01').returncode,0)
  for args in [('--case','missing'),('--max-requests','0'),('--fallback-only',)]:
   p=self.run_cli('smoke.py',*args);self.assertEqual(p.returncode,2);self.assertIn('usage:',p.stderr)
 def test_native_inventory_and_optional_search_are_separate_truthful_stages(self):
  for args in [(),('--search',)]:
   p=self.run_cli('codex_probe.py',*args);self.assertEqual(p.returncode,0,p.stderr);r=json.loads(p.stdout)
   self.assertEqual(r['model_turns'],0);self.assertEqual(r['tool_calls'],bool(args))
   tiny=next(x for x in r['servers'] if x['name']=='leo-search-tinyfish');self.assertEqual(tiny['retrieval_verified'],bool(args))
 def test_evidence_preserves_conflict_and_rejects_invalid_batch_atomically(self):
  rows=[{'url':'https://example.com/a?utm_source=x','content':'A','support':'supports','claim_ids':['甲']},{'url':'https://example.com/a','content':'A','support':'contradicts','claim_ids':['乙']}]
  p=self.run_cli('evidence_ledger.py',data='\n'.join(map(json.dumps,rows)))
  self.assertEqual(p.returncode,0);r=json.loads(p.stdout);self.assertEqual(r['duplicate_count'],2);self.assertEqual(r['support'],'unknown');self.assertEqual(set(r['claim_ids']),{'甲','乙'})
  p=self.run_cli('evidence_ledger.py',data=json.dumps(rows[0])+'\n{bad')
  self.assertEqual(p.returncode,2);self.assertEqual(p.stdout,'');self.assertNotIn('Traceback',p.stderr)
 def test_output_failure_keeps_results_in_stdout_without_repeating_research(self):
  p=self.run_cli('smoke.py','--case','exa-01','--output',self.home)
  self.assertEqual(p.returncode,2);self.assertEqual(json.loads(p.stdout)['passed'],1)
  self.assertNotIn('Traceback',p.stderr);self.assertIn('stdout',p.stderr)
