"""Offline S9-06 acceptance: real evidence, not timing assertions."""
import hashlib
import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import compare


class Tree4(unittest.TestCase):
    def test_identity_and_comparison(self):
        proof = json.loads((ROOT / 'build/s9/tree4-proof.json').read_text())
        binary = ROOT / 'build/s9/x86-tree4/milkyway_nbody.exe'
        self.assertEqual(proof['binary_sha256'], hashlib.sha256(binary.read_bytes()).hexdigest())
        for case in ('small', 'medium', 'large'):
            for threads in (1, 12):
                row = proof['runs']['%s-t%d' % (case, threads)]
                run, reference = ROOT / row['run'], ROOT / row['reference']
                # JSON's shortest round-trip float spelling also distinguishes signed zero.
                self.assertEqual(json.dumps(compare.load_run(reference), sort_keys=True),
                                 json.dumps(compare.load_run(run), sort_keys=True))
                self.assertEqual((run / 'exit.txt').read_text().strip(), '0')
                text = compare.captured_output(run)
                checks = re.findall(r'^TREE_IDENTITY step=(\d+).* PASS$', text, re.M)
                calls = int(re.search(r'^PHASE nbMakeTree \S+ (\d+)$', text, re.M)[1])
                self.assertEqual(list(map(int, checks)), [0] + list(range(calls - 1)))
                self.assertEqual(row['identity_builds'], calls)
                self.assertIn('PASS (strict absolute', row['compare'])
                frontiers = re.findall(r'^TREE_FRONTIER .* max=(\d+) limit=(\d+)$', text, re.M)
                self.assertEqual(len(frontiers), calls)
                self.assertTrue(all(int(maximum) <= int(limit) for maximum, limit in frontiers))

    def test_card_handoff_and_prediction(self):
        folder = ROOT / 'build/s9/card-tree4'
        self.assertEqual((folder / 'milkyway_nbody.mic').read_bytes()[:4], b'\x7fELF')
        self.assertIn('PASS: knc_lint exit 0', (folder / 'knc-lint.txt').read_text())
        options = (folder / '.build-options').read_text()
        for option in ('TREE_VARIANT=4', 'PARALLEL_QUAD=1', 'STATIC_INTEGRATE=1',
                       'PHASE_TIMERS=1', 'VECTOR_GRAVITY=0', 'FORCE_CHUNK=4', 'WALK_LAYOUT=0'):
            self.assertIn('-DNBODY_' + option, options)
        self.assertIn('-DNBODY_TREE_IDENTITY=0', options)
        self.assertIn('-O2', options)
        script = (ROOT / 'build/s9/tree4-window.sh').read_bytes()
        self.assertNotIn(b'\r', script)
        jobs = [line for line in script.decode().splitlines() if line.startswith('python tools/card_run ')]
        self.assertEqual(len(jobs), 2)
        for case, job in zip(('large', 'core-small'), jobs):
            for token in ('--benchmark', '--threads 240', '--nthreads 240', 'workunits/' + case):
                self.assertIn(token, job)
        manifest = json.loads((ROOT / 'build/s9/tree4-card-manifest.json').read_text())
        self.assertEqual(manifest['binary_sha256'], hashlib.sha256((folder / 'milkyway_nbody.mic').read_bytes()).hexdigest())
        for name, expected in manifest['files'].items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), expected, name)
        model = json.loads((ROOT / 'build/s9/tree4-model.json').read_text())
        self.assertEqual(model['baseline_partition_seconds'], 5.93)
        self.assertGreater(model['partition_seconds'], 0)
        self.assertLess(model['partition_seconds'], 5.93)
        self.assertFalse(model['model_table_used'])
        self.assertTrue((ROOT / 'build/s9/tree4-prediction.txt').read_text().strip())



if __name__ == '__main__':
    unittest.main()
