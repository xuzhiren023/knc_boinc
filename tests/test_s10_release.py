"""S10-01 acceptance: one combined release and retained proof/handoff."""
import hashlib
import json
import re
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'build/s10'
sys.path.insert(0, str(ROOT / 'scripts'))
import compare


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Release(unittest.TestCase):
    def test_release_options(self):
        env = (ROOT / 'config/release.env').read_text()
        for name, timers in (('card-release', 0), ('card-release-timers', 1), ('x86-release', 0)):
            options = (BUILD / name / '.build-options').read_text()
            for option in ('TREE_VARIANT=4', 'DF_REUSE=1', 'PARALLEL_QUAD=1', 'STATIC_INTEGRATE=1',
                           'FORCE_CHUNK=4', 'VECTOR_GRAVITY=0', 'WALK_LAYOUT=0', 'TREE_IDENTITY=0',
                           'WALK_COUNTERS=0', 'DF_STATS=0', 'DF_VECTOR=0', 'PHASE_TIMERS=%d' % timers):
                self.assertIn('-DNBODY_' + option, options)
            self.assertIn('-O2', options)
            self.assertNotIn('-O3', options)
        release = (BUILD / 'card-release/.build-options').read_text()
        timers = (BUILD / 'card-release-timers/.build-options').read_text()
        self.assertEqual(release.replace('NBODY_PHASE_TIMERS=0', 'NBODY_PHASE_TIMERS=1'), timers)
        self.assertIn('export PHASE_TIMERS=0', env)
        for filename, macros in (('nbody_tree.c', ('TREE_VARIANT',)),
                                 ('nbody_mixeddwarf.c', ('DF_REUSE', 'PARALLEL_QUAD')),
                                 ('nbody_plain.c', ('STATIC_INTEGRATE',))):
            source = (ROOT / 'third_party/milkywayathome_client_196/nbody/src' / filename).read_text()
            for macro in macros:
                self.assertRegex(source, r'#ifndef NBODY_' + macro + r'\s+#define NBODY_' + macro + r' 0')

    def test_identity_proof(self):
        proof = json.loads((BUILD / 'proof.json').read_text())
        for case in ('small', 'medium', 'large', 'core-small'):
            row = proof[case]
            self.assertEqual(row['threads'], 12)
            self.assertEqual(row['binary_sha256'], sha(BUILD / 'x86-release/milkyway_nbody.exe'))
            a, b = ROOT / row['reference'], ROOT / row['run']
            self.assertEqual(json.dumps(compare.load_run(a), sort_keys=True),
                             json.dumps(compare.load_run(b), sort_keys=True))
            self.assertEqual((b / 'exit.txt').read_text().strip(), '0')
            self.assertIn('PASS (strict absolute', row['compare'])
        bodies = proof['bodies']
        self.assertEqual(sha(ROOT / bodies['capture']), '7117b750caad318ab42a781346ca480a9f43fa1828e0832b58ad06fc00b88b59')
        for source in bodies['sources']:
            self.assertEqual((ROOT / bodies['capture']).read_bytes(), Path(source).read_bytes())
        self.assertGreater(proof['tree']['builds'], 0)
        tree = proof['tree']
        self.assertEqual(tree['binary_sha256'], sha(BUILD / 'x86-identity/milkyway_nbody.exe'))
        text = compare.captured_output(ROOT / tree['run'])
        checks = re.findall(r'^TREE_IDENTITY step=(\d+).* PASS$', text, re.M)
        calls = int(re.search(r'^PHASE nbMakeTree \S+ (\d+)$', text, re.M)[1])
        self.assertEqual(list(map(int, checks)), [0] + list(range(calls - 1)))
        self.assertEqual(tree['builds'], calls)
        self.assertEqual(tree['passes'], len(checks))

    def test_card_package_window(self):
        for variant in ('card-release', 'card-release-timers'):
            folder = BUILD / variant
            self.assertEqual((folder / 'milkyway_nbody.mic').read_bytes()[:4], b'\x7fELF')
            self.assertIn('PASS: knc_lint exit 0', (folder / 'knc-lint.txt').read_text())
        package = ROOT / 'dist/milkyway_package'
        self.assertEqual(sha(package / 'milkyway_nbody.mic'), sha(BUILD / 'card-release/milkyway_nbody.mic'))
        subprocess.run([sys.executable, str(ROOT / 'packaging/check_package.py'), str(package)], check=True)
        script = (BUILD / 'release-window.sh').read_bytes()
        self.assertNotIn(b'\r', script)
        jobs = [line for line in script.decode().splitlines() if line.startswith('python tools/card_run ')]
        self.assertEqual(len(jobs), 2)
        for case, job in zip(('large', 'core-small'), jobs):
            for token in ('--benchmark', '--threads 240', '--nthreads 240', 'workunits/' + case,
                          'build/s10/card-release-timers/milkyway_nbody.mic'):
                self.assertIn(token, job)
        for name, expected in json.loads((BUILD / 'manifest.json').read_text()).items():
            self.assertEqual(sha(ROOT / name), expected, name)


if __name__ == '__main__':
    unittest.main()
