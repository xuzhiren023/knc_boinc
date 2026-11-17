"""S10-03 acceptance: phase accounting, exact output, one full run, card handoff."""
import hashlib
import json
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[1]
B = ROOT / 'build/s10/gen'
sys.path.insert(0, str(ROOT / 'scripts'))
import compare

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def read(name):
    return json.loads((B / name).read_text())

class Acceptance(unittest.TestCase):
    def test_profile_and_selection(self):
        p = read('selection.json')
        self.assertTrue(p['justification'])
        self.assertTrue(p['prediction'])
        for label in ('base-profile', 'selected-profile'):
            r = read(label + '.json')
            self.assertEqual(r['bodies'], 4000)
            self.assertEqual(r['integrals'], 59181)
            self.assertEqual(r['velocity_attempts'], 10247)
            self.assertEqual(r['radius_attempts'], 61168)
            self.assertEqual(r['rng_calls'], 188040)
            self.assertGreater(r['integrals'], 4000)
            self.assertGreaterEqual(r['velocity_attempts'], 4000)
            self.assertGreaterEqual(r['radius_attempts'], 4000)
            self.assertAlmostEqual(sum(r['exclusive'].values()), r['total_seconds'], delta=0.001)
            for key in ('nodes', 'quad_serial', 'dist_serial', 'max', 'rejection', 'radius', 'rng', 'components', 'body'):
                self.assertGreaterEqual(r['exclusive'][key], 0)
        self.assertIn('Instrumentation', (ROOT / 'patches/README.md').read_text())
        self.assertIn('Performance', (ROOT / 'patches/README.md').read_text())

    def test_core_identity(self):
        p = read('core-proof.json')
        ref = (ROOT / p['reference']).read_bytes()
        self.assertEqual(len(ref), 4000 * 56)
        self.assertEqual(sha(ROOT / p['reference']), '7117b750caad318ab42a781346ca480a9f43fa1828e0832b58ad06fc00b88b59')
        for label in ('base-profile', 'selected-profile', 'selected'):
            r = p[label]
            self.assertEqual((ROOT / r['bodies']).read_bytes(), ref)
            self.assertEqual(sha(ROOT / r['binary']), r['binary_sha256'])
            self.assertEqual(compare.compare((ROOT / p['reference']).parent, (ROOT / r['bodies']).parent, compare.TOLERANCE), 0)
            self.assertEqual(compare.load_run((ROOT / r['bodies']).parent)[0].hex(), p['likelihood_hex'])

    def test_full_identity(self):
        p = read('full-proof.json')
        actual = ROOT / p['bodies']
        self.assertEqual(len(actual.read_bytes()), 110000 * 56)
        self.assertEqual(sha(actual), 'd09e23bcd50852add7f7bea4f8c9e68f6d18e4d39b2a302503d4bceaad23209f')
        self.assertEqual(actual.read_bytes(), (ROOT / p['reference']).read_bytes())
        self.assertEqual(sha(ROOT / p['binary']), p['binary_sha256'])
        self.assertEqual(p['binary_sha256'], read('core-proof.json')['selected']['binary_sha256'])
        self.assertEqual(read('full-started.json')['binary_sha256'], p['binary_sha256'])
        self.assertEqual(read('full-reference-provenance.json')['params_sha256'], sha(ROOT / 'workunits/117676/params.lua'))

    def test_card_handoff(self):
        p = read('handoff.json')
        for name, expected in p['files'].items():
            self.assertEqual(sha(ROOT / name), expected, name)
        for label in ('card-profile', 'card-selected', 'card-selected-clean'):
            d = ROOT / 'build/s10' / label
            self.assertEqual((d / 'milkyway_nbody.mic').read_bytes()[:4], b'\x7fELF')
            self.assertIn('PASS: knc_lint exit 0', (d / 'knc-lint.txt').read_text())
            self.assertIn('-DNBODY_GEN_PROFILE=' + ('0' if label.endswith('clean') else '1'), (d / '.build-options').read_text())
            self.assertIn('-DNBODY_GEN_PIPELINE=' + ('0' if label == 'card-profile' else '1'), (d / '.build-options').read_text())
            for opt in ('TREE_VARIANT=2', 'DF_REUSE=1', 'PARALLEL_QUAD=1', 'STATIC_INTEGRATE=1', 'FORCE_CHUNK=4', 'VECTOR_GRAVITY=0', 'WALK_LAYOUT=0'):
                self.assertIn('-DNBODY_' + opt, (d / '.build-options').read_text())
        script = (B / 'card-window.sh').read_text()
        self.assertEqual(script.count('tools/card_run --benchmark --threads 240'), 2)
        self.assertIn('Prediction:', script)
        self.assertTrue(p['prediction_recorded_utc'])

if __name__ == '__main__':
    unittest.main()
