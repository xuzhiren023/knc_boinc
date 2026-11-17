"""S10-09 acceptance: recompute measurements from retained raw evidence."""
import hashlib
import json
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
B = ROOT / 'build/s10/df-vector8'
sys.path.insert(0, str(ROOT / 'scripts'))
import compare
from importlib import import_module
driver = import_module('s10-df-special')

def read(name):
    return json.loads((B / name).read_text())

class Acceptance(unittest.TestCase):
    def test_card_result_match(self):
        folder=ROOT/'runs/card/s10-df-vector8'
        required=[folder/(v+'-'+c+'-240.json') for c in ['core-small','real-steps']
                  for v in ['release','vector8','scalar']]
        if not all(p.exists() for p in required) and os.environ.get('S10_REQUIRE_CARD')!='1':
            self.skipTest('Lead card likelihood results pending; use --card to require them')
        for case in ['core-small','real-steps']:
            exact=compare.load_run(folder/('release-'+case+'-240.txt'))[0]
            for variant in ['release','vector8','scalar']:
                label=variant+'-'+case+'-240'
                self.assertEqual(json.loads((folder/(label+'.json')).read_text())['exit_code'],0)
                self.assertEqual(compare.load_run(folder/(label+'.txt'))[0].hex(),exact.hex())
            for variant in ['guard','scalar-guard']:
                label=variant+'-'+case+'-240'
                if (folder/(label+'.json')).exists():
                    self.assertEqual(json.loads((folder/(label+'.json')).read_text())['exit_code'],0)
                    self.assertEqual(compare.load_run(folder/(label+'.txt'))[0].hex(),exact.hex())

    def test_relaxed_vector_experiment(self):
        kernel = read('kernel.json')
        self.assertGreater(kernel['samples'], 100)
        self.assertTrue(kernel['finite'])
        self.assertTrue(kernel['mixed_gamma_lanes'])
        self.assertTrue(kernel['partial_lane_isolation'])
        self.assertLess(kernel['max_node_normalized_error'], 0.01)
        self.assertLess(kernel['max_gamma_relative_error'], 1e-12)
        self.assertTrue(kernel['unsupported_original'])
        proof = read('differences.json')
        for case, count in [('core-small', 4000), ('real-steps', 20000)]:
            ref = ROOT / ('runs/s10-df-vector8/' + case + '-release/initial-bodies.bin')
            known = {'core-small':'7117b750caad318ab42a781346ca480a9f43fa1828e0832b58ad06fc00b88b59'}
            if case in known:
                self.assertEqual(hashlib.sha256(ref.read_bytes()).hexdigest(), known[case])
            for variant in ['vector8', 'guard', 'scalar', 'scalar-guard']:
                row = proof[case][variant]
                a, b = (ROOT / row[k] for k in ['reference', 'experiment'])
                self.assertEqual((a / 'initial-bodies.bin').stat().st_size, count * 56)
                self.assertEqual(driver.file_differences(a / 'initial-bodies.bin', b / 'initial-bodies.bin', 56),
                                 (row['different_bodies'], row['first_different_body']))
                self.assertEqual(driver.file_differences(a / 'rng.bin', b / 'rng.bin', row['rng_record_bytes']),
                                 (row['different_rng_states'], row['first_rng_divergence_body']))
                x, y = (compare.load_run(d)[0] for d in [a, b])
                self.assertEqual(row['likelihood_difference'], y - x)
                self.assertGreaterEqual(row['guard_triggers'], 0)
                stderr = (b / 'stderr.txt').read_text()
                self.assertIn('DF8_GUARD_TRIGGERS=' + str(row['guard_triggers']), stderr)
            for variant in ['release', 'vector8', 'guard', 'scalar', 'scalar-guard']:
                run = read(case + '-' + variant + '.json')
                self.assertEqual(hashlib.sha256((ROOT / run['binary']).read_bytes()).hexdigest(), run['binary_sha256'])
                self.assertEqual(run['threads'], 4)
                self.assertGreater(run['generation_seconds'], 0)
        calibration = read('calibration.json')
        self.assertGreater(calibration['comparisons'], 100)
        self.assertGreaterEqual(calibration['safety_factor'], 100)
        self.assertGreater(calibration['margin'], calibration['max_normalized_difference'])
        scalar_calibration = read('calibration-scalar.json')
        self.assertGreater(scalar_calibration['comparisons'], 100)
        self.assertGreater(scalar_calibration['margin'], scalar_calibration['max_normalized_difference'])
        handoff = read('handoff.json')
        for name, digest in handoff['files'].items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), digest, name)
        for variant in ['release', 'vector8', 'guard', 'scalar', 'scalar-guard']:
            out = B / ('card-' + variant)
            self.assertEqual((out / 'milkyway_nbody.mic').read_bytes()[:4], b'\x7fELF')
            self.assertIn('PASS: knc_lint exit 0', (out / 'knc-lint.txt').read_text())
            opts = (out / '.build-options').read_text()
            self.assertIn('-DNBODY_TREE_VARIANT=4', opts)
            if variant != 'release':
                self.assertIn('-DNBODY_DF_SPECIAL=1', opts)
                self.assertIn('-DNBODY_DF_VECTOR8=1', opts)
                self.assertIn('-mveclibabi=knc', opts)
            if variant in ['scalar', 'scalar-guard']:
                self.assertIn('-DNBODY_DF_VECTOR8_SCALAR_LOG_ATAN=1', opts)
        window = (B / 'card-window.sh').read_text()
        self.assertEqual(window.count('--transfer tcp-large'), 10)
        self.assertIn('Prediction:', window)
        self.assertTrue(handoff['prediction_recorded_utc'])
        self.assertIn('missed:', (B / 'compiler-items.txt').read_text())
        dis = (B / 'card-vector8/disassembly.txt').read_text()
        self.assertIn('<df8_nodes', dis)
        self.assertIn('vmulpd', dis)
        self.assertIn('__knc_vmath_core_pow_8', dis)
        self.assertTrue(read('twin-effort.json')['commands'])
        nodes = read('captured-node-differences.json')
        self.assertEqual(nodes['records'], 64)
        self.assertGreaterEqual(nodes['lanes'], 500)
        self.assertEqual(hashlib.sha256((B / 'twin-node-inputs.bin').read_bytes()).hexdigest(), nodes['source_sha256'])
        twin = read('twin-node-results.json')
        self.assertEqual(set(twin['entries']), {'scalar', 'vector8'})
        scalar_kernel = read('kernel-scalar.json')
        self.assertTrue(scalar_kernel['finite'])
        self.assertTrue(scalar_kernel['scalar_log_atan_exact'])
        self.assertTrue(scalar_kernel['scalar_log_atan_selected'])
        self.assertTrue(scalar_kernel['partial_lane_isolation'])
        self.assertEqual(set(read('twin-node-results-scalar.json')['entries']), {'scalar', 'vector8'})
        cancellation=read('full-cancellation.json')
        self.assertEqual(cancellation['active_full_jobs'],0)
        self.assertFalse(any(v['started'] for v in cancellation['variants'].values()))

if __name__ == '__main__':
    unittest.main()
