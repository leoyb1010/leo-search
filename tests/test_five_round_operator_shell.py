"""Execute bootstrap/update/proxy flows without network or a real installation."""
import os, shutil, subprocess, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class OperatorShellTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name);self.bin=self.home/'bin';self.bin.mkdir()
  git=self.bin/'git';git.write_text('''#!/bin/sh
printf '%s\\n' "$*" >> "$HOME/git-calls"
case "$*" in
 *"rev-parse --is-inside-work-tree"*) exit "${FAKE_REVPARSE_EXIT:-0}" ;;
 *"remote get-url origin"*) echo "${FAKE_ORIGIN:-https://github.com/leoyb1010/leo-search.git}" ;;
 *"pull --ff-only"*) exit "${FAKE_PULL_EXIT:-0}" ;;
 "clone "*) mkdir -p "$HOME/plugins/leo-search/.git" "$HOME/plugins/leo-search/scripts"; cp "$HOME/install-fixture" "$HOME/plugins/leo-search/scripts/install.sh" ;;
esac
''');git.chmod(0o755)
  self.installer=self.home/'install-fixture';self.installer.write_text('#!/bin/sh\necho installed >> "$HOME/install-calls"\n');self.installer.chmod(0o755)
  self.env={**os.environ,'HOME':str(self.home),'PATH':str(self.bin)+os.pathsep+os.environ['PATH'],'LEO_SEARCH_PROXY_FILE':str(self.home/'proxy')}
 def tearDown(self):self.tmp.cleanup()
 def call(self,name,*args,extra=None):return subprocess.run(['sh',str(ROOT/'scripts'/name),*args],env={**self.env,**(extra or {})},text=True,capture_output=True,timeout=5)
 def existing(self):
  p=self.home/'plugins/leo-search';(p/'.git').mkdir(parents=True);(p/'scripts').mkdir();shutil.copy2(self.installer,p/'scripts/install.sh');return p
 def test_bootstrap_fresh_repeated_ff_only_and_failed_pull(self):
  self.assertEqual(self.call('bootstrap.sh').returncode,0)
  self.assertEqual(self.call('bootstrap.sh').returncode,0)
  self.assertIn('pull --ff-only',(self.home/'git-calls').read_text())
  self.assertEqual(self.call('bootstrap.sh',extra={'FAKE_PULL_EXIT':'17'}).returncode,17)
  self.assertEqual((self.home/'install-calls').read_text().splitlines(),['installed','installed'])
 def test_bootstrap_conflicting_path_or_origin_preserves_existing_data(self):
  p=self.home/'plugins/leo-search';p.mkdir(parents=True);(p/'keep').write_text('original')
  self.assertEqual(self.call('bootstrap.sh').returncode,73);self.assertEqual((p/'keep').read_text(),'original')
  (p/'.git').mkdir()
  self.assertEqual(self.call('bootstrap.sh',extra={'FAKE_ORIGIN':'https://example.com/other.git'}).returncode,73)
  self.assertFalse((self.home/'install-calls').exists())
 def test_update_ff_only_and_failure_do_not_install(self):
  p=self.existing();shutil.copy2(ROOT/'scripts/update.sh',p/'scripts/update.sh')
  for status in ['0','19']:
   r=subprocess.run(['sh',str(p/'scripts/update.sh')],env={**self.env,'FAKE_PULL_EXIT':status},capture_output=True,text=True)
   self.assertEqual(r.returncode,int(status))
  self.assertEqual((self.home/'install-calls').read_text().splitlines(),['installed'])
  (p/'.git').rmdir();r=subprocess.run(['sh',str(p/'scripts/update.sh')],env=self.env,capture_output=True,text=True);self.assertEqual(r.returncode,69)
 def test_proxy_child_environment_arguments_exit_and_parent_unchanged(self):
  for extra,expected in [({'LEO_SEARCH_PROXY':'http://127.0.0.1:9000'},'http://127.0.0.1:9000'),({'LEO_SEARCH_PROXY':''},'http://127.0.0.1:9100')]:
   (self.home/'proxy').write_text('http://127.0.0.1:9100\n')
   r=self.call('with_proxy.sh','sh','-c','printf "%s|%s|%s|%s" "$HTTP_PROXY" "$HTTPS_PROXY" "$ALL_PROXY" "$1"; exit 23','fixture','two words',extra=extra)
   self.assertEqual(r.returncode,23);self.assertEqual(r.stdout,'|'.join([expected]*3+['two words']))
   self.assertNotIn('ALL_PROXY',extra)

 def test_explicit_proxy_overrides_lowercase_without_changing_no_proxy(self):
  extra={'LEO_SEARCH_PROXY':'http://127.0.0.1:9000','http_proxy':'http://old:80','https_proxy':'http://old:81','all_proxy':'socks5://old:82','NO_PROXY':'localhost','no_proxy':'localhost'}
  r=self.call('with_proxy.sh','python3','-c','import os,json;print(json.dumps({k:os.environ.get(k) for k in ["HTTP_PROXY","HTTPS_PROXY","ALL_PROXY","http_proxy","https_proxy","all_proxy","NO_PROXY","no_proxy"]}))',extra=extra)
  import json
  self.assertEqual(r.returncode,0);values=json.loads(r.stdout)
  for k in ['HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy']:self.assertEqual(values[k],extra['LEO_SEARCH_PROXY'])
  self.assertEqual(values['NO_PROXY'],'localhost');self.assertEqual(values['no_proxy'],'localhost')
 def test_no_selected_proxy_preserves_inherited_child_environment(self):
  r=self.call('with_proxy.sh','sh','-c','printf "%s|%s" "$https_proxy" "$HTTPS_PROXY"',extra={'LEO_SEARCH_PROXY':'','https_proxy':'http://lower:80','HTTPS_PROXY':'http://upper:81'})
  self.assertEqual(r.returncode,0);self.assertEqual(r.stdout,'http://lower:80|http://upper:81')
 def test_missing_command_reports_usage_instead_of_false_success(self):
  r=self.call('with_proxy.sh');self.assertEqual(r.returncode,64);self.assertEqual(r.stdout,'');self.assertIn('usage:',r.stderr)
 def test_gitfile_worktree_update_and_bootstrap_remain_ff_only(self):
  p=self.existing();(p/'.git').rmdir();(p/'.git').write_text('gitdir: synthetic-worktree')
  shutil.copy2(ROOT/'scripts/update.sh',p/'scripts/update.sh')
  r=subprocess.run(['sh',str(p/'scripts/update.sh')],env=self.env,capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr)
  self.assertEqual(self.call('bootstrap.sh').returncode,0)
  calls=(self.home/'git-calls').read_text();self.assertEqual(calls.count('rev-parse --is-inside-work-tree'),2);self.assertEqual(calls.count('pull --ff-only'),2)

 def test_invalid_gitfile_is_rejected_before_pull_or_install(self):
  p=self.existing();(p/'.git').rmdir();(p/'.git').write_text('invalid gitfile')
  shutil.copy2(ROOT/'scripts/update.sh',p/'scripts/update.sh')
  env={**self.env,'FAKE_REVPARSE_EXIT':'128'}
  r=subprocess.run(['sh',str(p/'scripts/update.sh')],env=env,capture_output=True,text=True);self.assertEqual(r.returncode,69)
  self.assertEqual(self.call('bootstrap.sh',extra={'FAKE_REVPARSE_EXIT':'128'}).returncode,73)
  self.assertNotIn('pull',(self.home/'git-calls').read_text());self.assertFalse((self.home/'install-calls').exists())
