"""S1-04 acceptance: evidenced verdict plus runnable probe/compare/twin handoff."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[1]
class Acceptance(unittest.TestCase):
    def test_verdict_and_handoff(self):
        for name in ('probes/libm_probe.c', 'scripts/probe-commands.sh', 'scripts/compare_probe.py', 'twin/diagnose_log.py', 'twin/log-diagnosis.json'):
            self.assertTrue((ROOT/name).is_file(), name)
        evidence = json.loads((ROOT/'twin/log-diagnosis.json').read_text())
        self.assertTrue(evidence['memory_reads'])
        self.assertEqual(16,len(evidence['cases']))
        self.assertTrue(all(c['status']=='functional_mismatch' for c in evidence['cases']))
        for read in evidence['memory_reads']:
            self.assertNotIn('UNINITIALIZED BYTE',read['sources'])
            if read['section']=='.rodata': self.assertIs(True,read['matches_ELF'])
        first=evidence['first_divergence']
        self.assertEqual('fildl',first['op'])
        self.assertEqual(8,first['bytes_read']['bytes'])
        self.assertEqual(0,first['hand_expected_integer'])
        self.assertEqual('functional_mismatch',json.loads((ROOT/'twin/fildl-repro/result.json').read_text())['status'])
        self.assertIn('output=0000000000000000',(ROOT/'twin/fildl-host.txt').read_text())
        manifest=json.loads((ROOT/'twin/probe-manifest.json').read_text())
        self.assertEqual(20776,manifest['probe_rows'])
        self.assertTrue(any('build/card/crlibm/log.c.o'==f['path'] for f in manifest['files']))
        report = (ROOT/'docs/twin-check.md').read_text()
        self.assertNotIn('{{', report)
        self.assertIn('S1-04', report)
        self.assertIn('fprintf',report)
        references=json.loads((ROOT/'twin/reference-runs.json').read_text())
        self.assertEqual(6,len(references))
        self.assertTrue(all(r['exit.txt']=='0' and r['histogram_present'] for r in references))
        self.assertNotIn('pending',report)
        self.assertIn('-fno-math-errno',(ROOT/'mk/sources.mk').read_text())
        # The handoff compare must both accept runner output and detect a real bit difference.
        with tempfile.TemporaryDirectory(dir=str(ROOT/'build/tmp')) as tmp:
            a,b=Path(tmp)/'a.txt',Path(tmp)/'b.txt'
            a.write_text('captured log_rn 3ff0000000000000 0000000000000000 0000000000000000\n')
            b.write_text(a.read_text()+'{"exit_code": 0}\n')
            cmd=[sys.executable,str(ROOT/'scripts/compare_probe.py'),str(a),str(b)]
            self.assertEqual(0,subprocess.run(cmd,capture_output=True).returncode)
            b.write_text(a.read_text().replace(' 0000000000000000\n',' 0000000000000001\n'))
            bad=subprocess.run(cmd,capture_output=True,text=True)
            self.assertEqual(1,bad.returncode)
            self.assertIn('host=0000000000000000 card=0000000000000001',bad.stdout)
if __name__ == '__main__': unittest.main()
