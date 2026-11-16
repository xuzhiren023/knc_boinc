"""S5-01 acceptance: ranking evidence/document and ignored regenerated files."""
import json
from pathlib import Path
import subprocess
import unittest
ROOT = Path(__file__).resolve().parents[1]

class TwinFlagsTest(unittest.TestCase):
    def test_experiment_and_document(self):
        evidence = json.loads((ROOT/'twin/flags/evidence.json').read_text())
        self.assertEqual(evidence['inputs'], ['small', 'large-0', 'large-128', 'large-256', 'large-384'])
        self.assertEqual(len(evidence['variants']), 4)
        for variant in evidence['variants']:
            self.assertEqual(list(variant['cases']), evidence['inputs'])
            if variant['name'] in ['V1', 'V2']:
                self.assertTrue(all(c['functional']['status'] == 'not_run' and c['extraction']['status'] == 'invalid_input' for c in variant['cases'].values()))
                continue
            for case in variant['cases'].values():
                if not variant['whole_function']:
                    self.assertTrue(case['functional']['region_cut']['retained_records_identical'])
                    self.assertFalse(case['functional']['cold_exit_executed'])
            for case in variant['cases'].values():
                self.assertEqual(case['functional']['status'], 'ok')
                self.assertEqual(case['simulate']['status'], 'ok')
                self.assertEqual(case['simulate']['profile']['id'], 'card-7120-measured')
        self.assertEqual(set(evidence['batches']), set(evidence['inputs']))
        variants = {v['name']:v for v in evidence['variants']}
        for case_name, batch in evidence['batches'].items():
            self.assertEqual(batch['status'], 'ok')
            self.assertEqual(set(batch['prediction']['ranking']), {'V0', 'V3'})
            for row in batch['prediction']['candidates']:
                simulate = variants[row['name']]['cases'][case_name]['simulate']
                self.assertEqual(row['predicted_cycles_per_unit'], simulate['prediction']['predicted_cycles_per_unit'])
                self.assertEqual(batch['profile']['hash'], simulate['profile']['hash'])
        self.assertEqual(evidence['schedule']['status'], 'unsupported')
        self.assertIn('interior', evidence['schedule']['message'])
        self.assertEqual(len(evidence['native']), 2)
        for result in evidence['native']:
            self.assertEqual(result['status'], 'invalid_input')
            self.assertIn('memory blocks span', result['message'])
        handoff = (ROOT/'twin/flags/run-native.sh').read_text()
        self.assertIn('build/flags/V0/milkyway_nbody.mic', handoff)
        self.assertIn('build/flags/'+evidence['top_candidate']+'/milkyway_nbody.mic', handoff)
        text = (ROOT/'docs/twin-flags.md').read_text()
        for term in ['too close for the twin', 'result_class', 'limiting_constraints', 'No card', 'V0', 'V1', 'V2', 'V3']:
            self.assertIn(term, text)

    def test_large_files_ignored(self):
        paths = ['twin/flags/V0/small.json', 'twin/flags/V0/app.disassembly.txt',
                 'twin/flags/V0/small-simulate/result.json', 'twin/flags/native-V0/kernel.json',
                 'twin/flags/V0/small-full.json', 'twin/flags/V0/small-functional/trace.json',
                 'twin/flags/coalesced-inputs/input.bin']
        run = subprocess.run(['git', 'check-ignore', '--no-index', *paths], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(set(run.stdout.splitlines()), set(paths))

if __name__ == '__main__':
    unittest.main()
