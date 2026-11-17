"""S8-09 acceptance against real artifacts; missing evidence fails closed.

Run after scripts/s8-09.sh proof. --host omits only the native speed gate.
"""
import hashlib
import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / 'runs/s8-09/final'
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'tests')]
import compare
from force_chunk_matrix import science


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Integration(unittest.TestCase):
    def test_patch_classes(self):
        readme = (ROOT / 'patches/README.md').read_text()
        classes = re.findall(r'^\| `([^`]+\.patch)` \| (Correctness/portability|Performance|Instrumentation) \|', readme, re.M)
        for path in (ROOT / 'patches').rglob('*.patch'):
            name = path.relative_to(ROOT / 'patches').as_posix()
            self.assertEqual(sum(entry[0] == name for entry in classes), 1,
                             'patch must have exactly one class: ' + name)

    def test_science_and_generator_identity(self):
        proof = json.loads((ROOT / 'build/s8-09/proof.json').read_text())
        self.assertEqual(proof['binary_sha256'], digest(ROOT / 'build/s8-09/x86-final/milkyway_nbody.exe'))
        release = json.loads((ROOT / 'build/s8-09/release-matrix.json').read_text())
        self.assertEqual(release['binary_sha256'], proof['binary_sha256'])
        variant = int(re.search(r'^export TREE_VARIANT=(\d+)$',
                               (ROOT / 'config/s8-09.env').read_text(), re.M)[1])
        self.assertEqual(proof['tree_changed'], variant != 0)
        for case in ('small', 'medium', 'large', 'core-small'):
            reference = ROOT / proof['references'][case]
            for threads in (1, 4, 12):
                out = RUNS / ('%s-t%d' % (case, threads))
                with self.subTest(case=case, threads=threads):
                    self.assertEqual((out / 'exit.txt').read_text().strip(), '0')
                    self.assertEqual(compare.compare(reference, out, compare.TOLERANCE), 0)
                    self.assertEqual(compare.load_run(reference)[0].hex(), compare.load_run(out)[0].hex())
                    self.assertEqual(science(reference), science(out))
                    if proof['tree_changed']:
                        identity = RUNS / ('tree-%s-t%d' % (case, threads))
                        self.assertEqual((identity / 'exit.txt').read_text().strip(), '0')
                        self.assertEqual(compare.load_run(reference), compare.load_run(identity))
                        text = (identity / 'stderr.txt').read_text()
                        calls = int(re.search(r'^PHASE nbMakeTree \S+ (\d+)$', text, re.M)[1])
                        checks = re.findall(r'^TREE_IDENTITY .*$', text, re.M)
                        self.assertEqual(len(checks), calls)
                        self.assertTrue(all(line.endswith('PASS') for line in checks))
                        self.assertEqual([int(re.search(r'step=(\d+)', line)[1]) for line in checks],
                                         [0] + list(range(calls - 1)))
        for case, count in (('core-small', 4000), ('full-117676', 110000)):
            off = RUNS / (case + '-bodies-reference.bin')
            on = RUNS / (case + '-bodies-final.bin')
            self.assertEqual(off.stat().st_size, count * 7 * 8)
            self.assertEqual(off.read_bytes(), on.read_bytes())
        self.assertEqual(digest(RUNS / 'core-small-bodies-reference.bin'),
                         json.loads((ROOT / 'workunits/core-small/reference.json').read_text())['initial_bodies_sha256'])
        full_reference = json.loads((RUNS / 'full-117676-reference-provenance.json').read_text())
        self.assertEqual(digest(RUNS / 'full-117676-bodies-reference.bin'),
                         full_reference['initial_bodies_sha256'])

    def test_card_build_and_package(self):
        binary = ROOT / 'build/s8-09/card/milkyway_nbody.mic'
        self.assertEqual(binary.read_bytes()[:4], b'\x7fELF')
        self.assertIn('PASS: knc_lint exit 0', (ROOT / 'build/s8-09/card/knc-lint.txt').read_text())
        package = ROOT / 'dist/milkyway_package'
        self.assertEqual(binary.read_bytes(), (package / binary.name).read_bytes())
        for runtime in ('libgomp.so.1', 'libstdc++.so.6', 'libgcc_s.so.1'):
            self.assertEqual((ROOT / 'dist/card' / runtime).read_bytes(), (package / runtime).read_bytes())
        batches = sorted((ROOT / 'build/s8-09').glob('card-batch-*.sh'))
        self.assertTrue(batches, 'no staged card batch')
        for batch in batches:
            self.assertNotIn(b'\r', batch.read_bytes(), 'card window scripts require LF line endings')
            commands = [line for line in batch.read_text().splitlines() if line.startswith('python ')]
            self.assertTrue(1 <= len(commands) <= 6)
            for line in commands:
                for token in ('--benchmark', '--threads 240', 'scripts/card-launch.sh OMP_NUM_THREADS=240', '--nthreads 240'):
                    self.assertIn(token, line)
                self.assertLessEqual(int(re.search(r'--timeout (\d+)', line)[1]), 900)

    def test_model_and_compiler_evidence(self):
        model = (ROOT / 'docs/research/s8-integration-model.md').read_text()
        for token in ('T_lb', 'T_pred', 'T_meas', 'Stock 1.96', '117676', 'Compiler items'):
            self.assertIn(token, model)
        evidence = json.loads((ROOT / 'build/s8-09/twin-evidence.json').read_text())
        self.assertTrue(evidence['commands'])
        self.assertGreaterEqual(evidence['host_seconds'], 0)
        for command in evidence['commands']:
            self.assertIn('status', command)
            self.assertTrue((ROOT / command['result']).is_file())

    def test_native_speed(self):
        path = ROOT / 'build/s8-09/card-results.json'
        self.assertTrue(path.is_file(), 'Native card results have not been supplied; the 2x goal is unproven')
        evidence = json.loads(path.read_text())
        binary_hash = digest(ROOT / 'build/s8-09/card/milkyway_nbody.mic')
        for case in ('large', 'core-small'):
            row = evidence[case]
            self.assertEqual(row['binary_sha256'], binary_hash)
            self.assertEqual(row['threads'], 240)
            self.assertTrue(row['bit_identical'])
            self.assertGreater(row['seconds'], 0)
            self.assertGreaterEqual(row['best_x86_12_seconds'] / row['seconds'], 2)
            self.assertGreater(row['stock_196_seconds'], 0)
        self.assertIn('full-117676-projection', evidence, 'Missing full-workunit projection')
        full = evidence['full-117676-projection']
        self.assertTrue(full['formula'])
        self.assertGreater(full['card_seconds'], 0)
        self.assertGreaterEqual(full['best_x86_12_seconds'] / full['card_seconds'], 2)


if __name__ == '__main__':
    host = '--host' in sys.argv
    if host:
        sys.argv.remove('--host')
        delattr(Integration, 'test_native_speed')
    unittest.main()
