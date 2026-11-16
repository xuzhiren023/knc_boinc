"""S1-05 acceptance: current rerun evidence and ignored regenerated inputs."""
import json
from pathlib import Path
import subprocess
import unittest
ROOT = Path(__file__).resolve().parents[1]

class Twin040Test(unittest.TestCase):
    def test_rerun_evidence(self):
        paths = ['fildl-repro', 'functional', 'simulate', 'bounds',
                 'hot/functional', 'hot/simulate', 'hot/bounds']
        paths += ['log-cases/' + name for name in
                  ['fixed-' + str(i) for i in range(7)] +
                  ['seed-%03d' % i for i in range(8)] + ['captured']]
        for path in paths:
            with self.subTest(path=path):
                result = json.loads((ROOT/'twin'/path/'result.json').read_text())
                self.assertEqual(result['status'], 'ok')
                self.assertEqual(result['engine_version'], '0.4.0')
        execution = json.loads((ROOT/'twin/gravity-execution.json').read_text())
        self.assertFalse(execution['cold_exit_executed'])
        self.assertTrue(execution['normal_return_executed'])
        reference = json.loads((ROOT/'twin/gravity-reference.json').read_text())
        self.assertEqual(reference['exit'], 0)
        self.assertTrue(all(s['tree_incest_diagnostics'] == 0 for s in reference['streams'].values()))
        text = (ROOT/'docs/twin-check.md').read_text()
        self.assertIn('S1-05', text)
        self.assertIn('0.4.0', text)
        self.assertIn('error branch', text)
        self.assertIn('No card comparison', text)

    def test_large_files_ignored(self):
        paths = ['twin/card.disassembly.txt', 'twin/card.symbols.disassembly.txt',
                 'twin/kernel.json', 'twin/log-kernel.json',
                 'twin/log-cases/fixed-0.json', 'twin/functional/final-memory.json', 'twin/gravity-full.json',
                 'twin/functional/trace.json', 'twin/simulate/issue-log.json']
        run = subprocess.run(['git', 'check-ignore', '--no-index', *paths], cwd=ROOT,
                             capture_output=True, text=True)
        self.assertEqual(set(run.stdout.splitlines()), set(paths))

if __name__ == '__main__':
    unittest.main()
