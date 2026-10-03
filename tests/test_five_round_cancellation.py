"""Round 5: interactive process-group cancellation with only a sleeping fake curl."""
import os, signal, subprocess, tempfile, time, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class DoctorCancellationTests(unittest.TestCase):
 def test_cancelled_json_doctor_exits_truthfully_and_removes_its_temporary_report(self):
  for sig in [signal.SIGINT,signal.SIGTERM,signal.SIGHUP]:
   with self.subTest(signal=sig),tempfile.TemporaryDirectory() as temporary:
    home=Path(temporary);binary=home/'bin';binary.mkdir();curl=binary/'curl'
    curl.write_text('#!/bin/sh\necho started >> "$HOME/started"\nsleep 30\n');curl.chmod(0o755)
    env={**os.environ,'HOME':temporary,'TMPDIR':temporary,'PATH':str(binary)+os.pathsep+os.environ['PATH'],'LEO_SEARCH_PROXY':'','LEO_SEARCH_PROXY_FILE':str(home/'no-proxy')}
    process=subprocess.Popen(['sh',str(ROOT/'scripts/doctor.sh'),'--json'],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
    try:
     limit=time.monotonic()+3
     while not (home/'started').exists() and time.monotonic()<limit:time.sleep(.02)
     self.assertTrue((home/'started').exists(),'fake provider did not start')
     os.killpg(process.pid,sig)
     stdout,stderr=process.communicate(timeout=4)
     self.assertEqual(process.returncode,128+sig,(stdout,stderr))
     self.assertEqual(stdout,'');self.assertNotIn('Traceback',stderr)
     self.assertEqual((home/'started').read_text().splitlines(),['started'])
     self.assertFalse(list(home.glob('leo-search-doctor.*')))
    finally:
     if process.poll() is None:
      os.killpg(process.pid,signal.SIGKILL);process.communicate(timeout=2)
