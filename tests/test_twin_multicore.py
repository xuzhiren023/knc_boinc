"""S1-06 acceptance: requested experiment evidence and ignored regenerated data."""
import json
from pathlib import Path
import subprocess
import unittest
ROOT = Path(__file__).resolve().parents[1]

class Acceptance(unittest.TestCase):
    def test_experiment_and_document(self):
        root = ROOT/'twin/multicore'
        evidence = json.loads((root/'evidence.json').read_text())
        self.assertEqual(evidence['slice_bodies'], 128)
        self.assertEqual(evidence['bodies_per_context_executed'], 128,
                         'one-body diagnostics do not satisfy the requested slice experiment')
        for name in ('core', 'unit', 'ring', 'compare-unit', 'compare-ring'):
            result = json.loads((root/name/'result.json').read_text())
            self.assertEqual(result['status'], 'ok', name)
        text = (ROOT/'docs/twin-multicore.md').read_text()
        for required in ('unvalidated_scenario_estimate', '43,656', '33,622',
                         '52', '240', '60', 'assumptions', 'unsupported', 'parameters_used'):
            self.assertIn(required, text)

    def test_large_files_ignored(self):
        paths = ['twin/multicore/capture.json', 'twin/multicore/core/result.json',
                 'twin/multicore/capture/blocks/00004.bin', 'twin/multicore/capture/nodes.bin',
                 'twin/multicore/core.json', 'twin/multicore/unit.json',
                 'twin/multicore/ring.json', 'twin/multicore/core/issue-log.json',
                 'twin/multicore/unit/final-memory.json']
        run = subprocess.run(['git', 'check-ignore', '--no-index', *paths], cwd=ROOT,
                             capture_output=True, text=True)
        self.assertEqual(set(run.stdout.splitlines()), set(paths))

if __name__ == '__main__':
    unittest.main()
