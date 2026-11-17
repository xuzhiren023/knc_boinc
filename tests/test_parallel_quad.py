"""S8-03 acceptance: actual generator bytes, likelihoods, timings and card handoff.
Run scripts/test-parallel-quad.sh first to generate the evidence.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare import load_run


class ParallelQuad(unittest.TestCase):
    def test_generator_identity_and_timing(self):
        base = ROOT / 'runs/s8-quad/off-12'
        expected = (base / 'initial-bodies.bin').read_bytes()
        self.assertEqual(len(expected), 4000 * 7 * 8)
        likelihood = load_run(base)[0]
        reference = json.loads((ROOT/'workunits/core-small/reference.json').read_text())
        self.assertEqual(hashlib.sha256(expected).hexdigest(), reference['initial_bodies_sha256'])
        self.assertEqual(likelihood.hex(), reference['likelihood_hex'])
        self.assertEqual(hashlib.sha256((ROOT/'workunits/core-small/OCS_data_2025_north_194.hist').read_bytes()).hexdigest(), reference['histogram_sha256'])
        for threads in (1, 4, 12):
            run = ROOT / f'runs/s8-quad/on-{threads}'
            with self.subTest(threads=threads):
                subprocess.run([sys.executable, str(ROOT/'scripts/compare.py'), str(base), str(run)], check=True)
                # compare.py is tolerant; this additional check requires exact double bits.
                self.assertEqual(likelihood.hex(), load_run(run)[0].hex())
                self.assertEqual(expected, (run/'initial-bodies.bin').read_bytes())
                self.assertEqual(load_run(base)[1:], load_run(run)[1:])
        for variant in ('off-12', 'on-1', 'on-4', 'on-12'):
            run = ROOT / f'runs/s8-quad/{variant}'
            self.assertEqual((run/'exit.txt').read_text().strip(), '0')
            self.assertIn('S8_X87_CW=027f worker_mismatches=0', (run/'stderr.txt').read_text())
            generation = float(re.search(r'S8_GENERATION_SECONDS=(\S+)', (run/'stderr.txt').read_text())[1])
            total = float((run/'seconds.txt').read_text())
            self.assertGreater(generation, 0)
            self.assertGreater(total, generation)
        self.assertTrue((ROOT/'patches/nbody-parallel-quad.patch').is_file())
        self.assertIn('PARALLEL_QUAD ?= 0', (ROOT/'mk/Makefile').read_text())

    def test_card_handoff(self):
        binary = ROOT/'build/s8/card-quad/milkyway_nbody.mic'
        self.assertEqual(binary.read_bytes()[:4], b'\x7fELF')
        self.assertIn('PASS: knc_lint exit 0', (ROOT/'build/s8/card-quad/knc-lint.txt').read_text())
        script = (ROOT/'scripts/quad-card-command.sh').read_text()
        for token in ('--benchmark', '--threads 240', 'OMP_NUM_THREADS=240', '--nthreads 240', '4.90652', '2.87629'):
            self.assertIn(token, script)
        for name in ('libgomp.so.1', 'libstdc++.so.6', 'libgcc_s.so.1'):
            self.assertTrue((ROOT/'dist/card'/name).is_file())


if __name__ == '__main__':
    unittest.main()
