"""Card-free acceptance for the lead's end-to-end launcher."""
import importlib.util
import json
import pathlib
import subprocess
import tempfile
import unittest
from unittest import mock
import contextlib
import io

ROOT = pathlib.Path(__file__).resolve().parents[1]


class EndToEnd(unittest.TestCase):
    def test_dry_run(self):
        result = subprocess.run(['bash', 'scripts/e2e_card.sh', '--dry-run',
                                 '--case', 'medium', '--threads', '4'], cwd=ROOT,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        self.assertEqual(result.returncode, 0, result.stdout)
        for token in ('ssh.exe', 'scp.exe', '192.168.1.100', 'xeon_phi_rsa',
                      '/tmp/claude/claude-knc-boinc', 'STOP', 'CONT', 'KILL',
                      'ps -o stat=', 'checkpoint.request', 'knc_checkpoint',
                      'snapshot', 'stdout.txt', 'stderr.txt', 'rm -rf',
                      '60 s', '30 s', 'restart', 'compare.py', 'live-card.png'):
            self.assertIn(token, result.stdout)
        self.assertNotIn('--fake-card', result.stdout)

    def test_ledger(self):
        spec = importlib.util.spec_from_file_location('e2e', ROOT / 'scripts/e2e_card.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # Exercise argument routing with every process launch forbidden.
        with mock.patch.object(module.subprocess, 'Popen', side_effect=AssertionError('process launched')), \
             mock.patch.object(module.subprocess, 'run', side_effect=AssertionError('process launched')), \
             mock.patch('sys.argv', ['e2e_card.py', '--dry-run']), contextlib.redirect_stdout(io.StringIO()):
            module.main()
        with tempfile.TemporaryDirectory(dir=ROOT / 'build') as tmp:
            ledger = pathlib.Path(tmp) / 'jobs.jsonl'
            def check(rows, blocked):
                ledger.write_text(''.join(json.dumps(r) + '\n' for r in rows))
                if blocked:
                    with self.assertRaises(RuntimeError):
                        module.check_ledger(ledger)
                else:
                    module.check_ledger(ledger)
            foreign = dict(jobId='other', project='gcc-knc', event='queued')
            check([foreign], True)
            check([dict(foreign, event='start')], True)
            for close in ('finish', 'superseded', 'cancelled', 'close'):
                check([foreign, dict(foreign, event=close)], False)
            check([dict(foreign, project='knc-boinc')], False)
            check([dict(foreign, project=None)], True)
            ledger.write_text('{broken\n')
            with self.assertRaises(RuntimeError):
                module.check_ledger(ledger)


if __name__ == '__main__':
    unittest.main()
