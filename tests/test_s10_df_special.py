"""S10-05 retained-evidence acceptance; fresh runs use test-s10-df-special.sh."""
import hashlib
import json
from pathlib import Path
import struct
import sys
import unittest
ROOT = Path(__file__).resolve().parents[1]
B = ROOT / 'build/s10/df-special'
sys.path.insert(0, str(ROOT / 'scripts'))
import compare

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def read(name):
    return json.loads((B / name).read_text())

def differences(a, b, width):
    assert len(a) == len(b) and len(a) % width == 0
    indices = [i // width for i in range(0, len(a), width) if a[i:i+width] != b[i:i+width]]
    return len(indices), indices[0] if indices else None

class Acceptance(unittest.TestCase):
    def test_exact_specialization(self):
        p = read('exact-proof.json')
        self.assertEqual(p['kernel_mismatches'], 0)
        self.assertGreater(p['kernel_samples'], 100)
        self.assertTrue(p['unsupported_models_original'])
        a, b = (ROOT / p[k] for k in ('reference', 'special'))
        self.assertEqual((a / 'initial-bodies.bin').read_bytes(), (b / 'initial-bodies.bin').read_bytes())
        self.assertEqual(sha(a / 'initial-bodies.bin'), '7117b750caad318ab42a781346ca480a9f43fa1828e0832b58ad06fc00b88b59')
        self.assertEqual(compare.load_run(a)[0].hex(), compare.load_run(b)[0].hex())
        report = (B / 'card-special-vec.txt').read_text()
        self.assertIn('missed:', report)
        self.assertIn('log_rn', report)
        self.assertIn('UpperIncompleteGammaFunc', report)

    def test_measured_relaxation(self):
        p = read('differences.json')
        self.assertGreater(read('vmath-kernel.json')['kernel_mismatches'], 0)
        for case, count in (('core-small', 4000), ('117676', 110000)):
            row = p[case]
            a, b = (ROOT / row[k] for k in ('reference', 'experiment'))
            aa, bb = (a / 'initial-bodies.bin').read_bytes(), (b / 'initial-bodies.bin').read_bytes()
            self.assertEqual(len(aa), count * 56)
            n, first = differences(aa, bb, 56)
            self.assertEqual((n, first), (row['different_bodies'], row['first_different_body']))
            # Exact PRNG state at the end of each body, before CM correction.
            n, first = differences((a / 'rng.bin').read_bytes(), (b / 'rng.bin').read_bytes(), row['rng_record_bytes'])
            self.assertEqual((n, first), (row['different_rng_states'], row['first_rng_divergence_body']))
            self.assertEqual(len((a / 'rng.bin').read_bytes()), count * row['rng_record_bytes'])
        core = p['core-small']
        x = compare.load_run(ROOT / core['reference'])[0]
        y = compare.load_run(ROOT / core['experiment'])[0]
        self.assertEqual(core['exact_likelihood_hex'], x.hex())
        self.assertEqual(core['experiment_likelihood_hex'], y.hex())
        self.assertEqual(core['likelihood_difference'], y - x)
        for label in ('special', 'vmath'):
            marker = read('full-' + label + '-started.json')
            row = read('full-' + label + '.json')
            self.assertEqual(marker['binary_sha256'], sha(ROOT / row['binary']))

    def test_timing_and_handoff(self):
        p = read('handoff.json')
        for name, digest in p['files'].items():
            self.assertEqual(sha(ROOT / name), digest, name)
        for label in ('release', 'special', 'vmath'):
            r = read('core-' + label + '.json')
            self.assertEqual(sha(ROOT / r['binary']), r['binary_sha256'])
            self.assertEqual(r['threads'], 12)
            self.assertGreater(r['generation_seconds'], 0)
            self.assertGreater(r['whole_seconds'], r['generation_seconds'])
        for label in ('special', 'vmath'):
            out = B / ('card-' + label)
            self.assertEqual((out / 'milkyway_nbody.mic').read_bytes()[:4], b'\x7fELF')
            self.assertIn('PASS: knc_lint exit 0', (out / 'knc-lint.txt').read_text())
            options = (out / '.build-options').read_text()
            self.assertIn('-DNBODY_DF_SPECIAL=1', options)
            self.assertIn('-DNBODY_TREE_VARIANT=4', options)
            self.assertIn('-DNBODY_GEN_PROFILE=0', options)
            if label == 'vmath':
                self.assertIn('-mveclibabi=knc', options)
        release_options = (B / 'card-release/.build-options').read_text()
        self.assertIn('-DNBODY_DF_SPECIAL=0', release_options)
        self.assertIn('-DNBODY_DF_VMATH=0', release_options)
        script = (B / 'card-window.sh').read_text()
        self.assertEqual(script.count('tools/card_run --benchmark --threads 240'), 3)
        self.assertIn('Prediction:', script)
        self.assertTrue(p['prediction_recorded_utc'])
        self.assertIn('Performance', (ROOT / 'patches/README.md').read_text())

if __name__ == '__main__':
    unittest.main()
