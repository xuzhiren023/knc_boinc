"""S1-07 evidence; incomplete scaling stays an explicit expected failure."""
import json
from pathlib import Path
import subprocess
import unittest
ROOT = Path(__file__).resolve().parents[1]

class Acceptance(unittest.TestCase):
    def test_mismatch_isolated_and_documented(self):
        root = ROOT/'twin/multicore'
        evidence = json.loads((root/'isolation.json').read_text())
        self.assertEqual(evidence['body_indices'], [1024, 1408, 1664, 3072, 3200, 3584])
        self.assertEqual(len(evidence['core_runs']), 6)
        self.assertEqual(evidence['odd_one_out'], 'twin')
        for run in evidence['core_runs']:
            self.assertEqual(run['status'], 'functional_mismatch')
            self.assertEqual(run['scale'], 'core')
            self.assertEqual(run['contexts'], [0])
            self.assertEqual(run['engine_version'], '0.4.0')
            self.assertEqual(len(run['functional_check']['mismatches']), 1)
            self.assertTrue(run['operation_differences'])
        self.assertEqual(evidence['source_replay']['matched_components'], 18)
        self.assertTrue(evidence['rounding_proof']['native_result_is_closer'])
        repro = json.loads((ROOT/'twin/x87-rounding-repro/result.json').read_text())
        self.assertEqual(repro['status'], 'functional_mismatch')
        text = (ROOT/'docs/twin-multicore.md').read_text()
        self.assertTrue(text.startswith('The twin'))
        for required in ('unvalidated_scenario_estimate', '43,656', '33,622',
                         '52', '240', '60', 'assumptions', 'unsupported', 'parameters_used',
                         '0x027f', '1e-10', 'double rounding'):
            self.assertIn(required, text)

    @unittest.expectedFailure
    def test_128_body_scaling_blocked_by_twin_x87_double_rounding(self):
        """Blocker: unchanged knc-twin 0.4.0 fails native-PC53 arithmetic repro."""
        root = ROOT/'twin/multicore'
        evidence = json.loads((root/'chunk-evidence.json').read_text())
        self.assertEqual(evidence['requested_bodies_per_context'], 128)
        self.assertTrue(evidence['build']['callee_identical_except_linker_relocations'])
        self.assertTrue(evidence['requested_experiment_complete'], evidence['blocker'])
        for name in ('baseline', 'unit', 'ring', 'compare-unit', 'compare-ring'):
            self.assertEqual(evidence['runs'][name]['status'], 'ok', name)

    def test_large_files_ignored(self):
        paths = ['twin/multicore/capture.json', 'twin/multicore/core/result.json',
                 'twin/multicore/capture/blocks/00004.bin', 'twin/multicore/capture/nodes.bin',
                 'twin/multicore/core.json', 'twin/multicore/unit.json',
                 'twin/multicore/ring.json', 'twin/multicore/core/issue-log.json',
                 'twin/multicore/unit/final-memory.json', 'twin/multicore/body-1024.json',
                 'twin/multicore/body-1024/result.json', 'twin/multicore/chunk-baseline.json',
                 'twin/multicore/chunk-ring/result.json']
        run = subprocess.run(['git', 'check-ignore', '--no-index', *paths], cwd=ROOT,
                             capture_output=True, text=True)
        self.assertEqual(set(run.stdout.splitlines()), set(paths))

if __name__ == '__main__':
    unittest.main()
