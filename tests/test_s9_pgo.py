"""S9-01 acceptance: artifacts, PGO identity, and the lead's staged jobs."""
import json
import hashlib
from pathlib import Path
import subprocess
import shlex
import unittest

ROOT = Path(__file__).resolve().parents[1]

class Acceptance(unittest.TestCase):
    def test_card_builds(self):
        for variant in ('card-base', 'card-pgo-train'):
            folder = ROOT / 'build/s9' / variant
            self.assertEqual((folder / 'milkyway_nbody.mic').read_bytes()[:4], b'\x7fELF')
            self.assertIn('PASS: knc_lint exit 0', (folder / 'knc-lint.txt').read_text())
        self.assertTrue((ROOT / 'scripts/pgo-use.sh').is_file())
        options = (ROOT / 'build/s9/card-base/.build-options').read_text()
        for flag in ('-O2', '-ffp-contract=off', '-DNBODY_TREE_VARIANT=2',
                     '-DNBODY_PARALLEL_QUAD=1', '-DNBODY_STATIC_INTEGRATE=1',
                     '-DNBODY_PHASE_TIMERS=1', '-DNBODY_VECTOR_GRAVITY=0',
                     '-DNBODY_FORCE_CHUNK=4', '-DNBODY_WALK_LAYOUT=0'):
            self.assertIn(flag, options)
        self.assertIn('-fprofile-update=atomic',
                      (ROOT / 'build/s9/card-pgo-train/.training-options').read_text())

    def test_host_bit_identity(self):
        proof = json.loads((ROOT / 'build/s9/x86-proof.json').read_text())
        self.assertNotIn('Wmissing-profile',
                         (ROOT / 'build/s9/x86-pgo-build.log').read_text())
        self.assertEqual(set(proof), {'small', 'medium', 'large'})
        for result in proof.values():
            self.assertEqual(result['threads'], 12)
            self.assertEqual(result['baseline_bits'], result['pgo_bits'])
            self.assertIn('abs=0 rel=0', result['compare'])
            for variant, key in [('x86-base', 'baseline_sha256'), ('x86-pgo', 'pgo_sha256')]:
                binary = ROOT / 'build/s9' / variant / 'milkyway_nbody.exe'
                self.assertEqual(result[key], hashlib.sha256(binary.read_bytes()).hexdigest())

    def test_launch_and_jobs(self):
        launcher = ROOT / 'scripts/card-launch-env.sh'
        # The launcher accepts an explicit program following all assignments.
        run = subprocess.run(['C:/Program Files/Git/bin/bash.exe', str(launcher),
                              'S9_A=first', 'S9_B=second value', '/bin/sh', '-c',
                              'printf "%s|%s" "$S9_A" "$S9_B"'],
                             capture_output=True, text=True, check=True)
        self.assertEqual(run.stdout, 'first|second value')
        for name, count in [('pgo-train.sh', 2), ('card-threads.sh', 8)]:
            data = (ROOT / 'build/s9' / name).read_bytes()
            self.assertNotIn(b'\r', data)
            self.assertEqual(data.count(b'--benchmark'), count)
            self.assertEqual(data.count(b'--threads 240'), count)
            self.assertEqual(data.count(b'# Reason:'), count)
            commands = [shlex.split(line) for line in data.decode().splitlines()
                        if line.startswith('python ')]
            for command in commands:
                self.assertIn('--timeout', command)
                self.assertEqual(command[command.index('--timeout') + 1], '900')
            if name == 'card-threads.sh':
                self.assertEqual({a for command in commands for a in command
                                  if a.startswith('OMP_NUM_THREADS=')},
                                 {'OMP_NUM_THREADS=120', 'OMP_NUM_THREADS=180', 'OMP_NUM_THREADS=240'})

if __name__ == '__main__':
    unittest.main()
