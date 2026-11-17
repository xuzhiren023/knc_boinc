"""S9-05 acceptance: generated evidence, never inferred from selected flags."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'build/s9/df'
sys.path.insert(0, str(ROOT / 'scripts'))
import compare

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

class Acceptance(unittest.TestCase):
    def test_reuse_core(self):
        proof = json.loads((BUILD / 'core-proof.json').read_text())
        a, b = [ROOT / proof[k]['bodies'] for k in ('base', 'reuse')]
        self.assertEqual(len(a.read_bytes()), 4000 * 7 * 8)
        self.assertEqual(a.read_bytes(), b.read_bytes())
        self.assertEqual(proof['base']['likelihood_hex'], proof['reuse']['likelihood_hex'])
        self.assertEqual((ROOT / proof['final']['bodies']).read_bytes(), a.read_bytes())
        self.assertEqual(proof['final']['likelihood_hex'], proof['base']['likelihood_hex'])
        self.assertEqual(sha(ROOT / proof['final']['binary']), proof['final']['binary_sha256'])
        for k in ('base', 'reuse', 'final'):
            self.assertEqual(proof[k]['threads'], 12)
            self.assertGreater(proof[k]['generation_seconds'], 0)
            self.assertEqual(sha(ROOT / proof[k]['binary']), proof[k]['binary_sha256'])
            folder = (ROOT / proof[k]['bodies']).parent
            self.assertEqual(compare.load_run(folder)[0].hex(), proof[k]['likelihood_hex'])

    def test_vector_experiment(self):
        proof = json.loads((BUILD / 'vector-proof.json').read_text())
        self.assertEqual(proof['bodies'], 4000)
        self.assertEqual(sha(ROOT / proof['binary']), proof['binary_sha256'])
        self.assertEqual((ROOT / proof['capture']).read_bytes(),
                         (ROOT / 'runs/s9-df/reuse/initial-bodies.bin').read_bytes())
        self.assertTrue(0 <= proof['fallbacks'] <= proof['bodies'])
        self.assertGreater(proof['generation_seconds'], 0)
        self.assertTrue((ROOT / 'docs/research/s9-df-bound.md').is_file())
        self.assertIn('PASS sample enclosures=2048 node enclosures=1024', (BUILD / 'kernel.txt').read_text())
        if proof['kept']:
            self.assertLess(proof['fallbacks'], proof['bodies'] / 2)
            self.assertTrue(proof['faster'])
        else:
            self.assertTrue(proof['fallbacks'] >= proof['bodies'] / 2 or not proof['faster'])
        self.assertEqual(proof['likelihood_hex'], json.loads((BUILD / 'core-proof.json').read_text())['reuse']['likelihood_hex'])

    def test_card_handoff(self):
        proof = json.loads((BUILD / 'vector-proof.json').read_text())
        for variant in ['card-dfreuse'] + (['card-dfvec'] if proof['kept'] else []):
            folder = ROOT / 'build/s9' / variant
            self.assertEqual((folder / 'milkyway_nbody.mic').read_bytes()[:4], b'\x7fELF')
            self.assertIn('PASS: knc_lint exit 0', (folder / 'knc-lint.txt').read_text())
            options = (folder / '.build-options').read_text()
            for flag in ('TREE_VARIANT=2', 'PARALLEL_QUAD=1', 'STATIC_INTEGRATE=1', 'PHASE_TIMERS=1', 'VECTOR_GRAVITY=0', 'FORCE_CHUNK=4', 'DF_REUSE=1'):
                self.assertIn('-DNBODY_' + flag, options)
            self.assertIn('-O2', options)
        manifest = json.loads((BUILD / 'handoff-manifest.json').read_text())
        for name, expected in manifest.items():
            self.assertEqual(sha(ROOT / name), expected, name)
        text = (BUILD / 'card-commands.sh').read_text()
        self.assertIn('tools/card_run --benchmark --threads 240', text)
        self.assertIn('scripts/card-launch.sh OMP_NUM_THREADS=240', text)
        self.assertEqual(text.count('tools/card_run --benchmark'), 2 if proof['kept'] else 1)
        for runtime in ('libgomp.so.1', 'libgcc_s.so.1', 'libstdc++.so.6'):
            self.assertEqual((BUILD / 'runtimes' / runtime).read_bytes()[:4], b'ELF')

    def test_full_final(self):
        proof = json.loads((BUILD / 'full-proof.json').read_text())
        actual, reference = [ROOT / proof[k] for k in ('capture', 'reference')]
        self.assertEqual(len(actual.read_bytes()), 110000 * 7 * 8)
        self.assertEqual(actual.read_bytes(), reference.read_bytes())
        self.assertEqual(sha(actual), proof['sha256'])
        provenance = json.loads((BUILD / 'full-reference-provenance.json').read_text())
        self.assertEqual(provenance['initial_bodies_sha256'], proof['sha256'])
        self.assertEqual(provenance['params_sha256'], sha(ROOT / 'workunits/117676/params.lua'))
        self.assertEqual(provenance['source_commit'], '1e640779f1cabf88aaa49e4db569cfe7e09016c4')
        self.assertEqual(sha(ROOT / proof['binary']), proof['binary_sha256'])
        core = json.loads((BUILD / 'core-proof.json').read_text())
        self.assertEqual(proof['binary_sha256'], core['final']['binary_sha256'])

if __name__ == '__main__':
    unittest.main()
