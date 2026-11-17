"""S10 release proof and lead-only two-job card window."""
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys

import compare
import s8_integration as harness

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'build/s10'
RUNS = ROOT / 'runs/s10'
sha = harness.sha


def relative(path):
    return path.relative_to(ROOT).as_posix()


def exact(reference, run):
    output = subprocess.check_output([sys.executable, str(ROOT / 'scripts/compare.py'),
                                      str(reference), str(run)], text=True)
    assert json.dumps(compare.load_run(reference), sort_keys=True) == json.dumps(
        compare.load_run(run), sort_keys=True), 'exact science mismatch: ' + str(run)
    print(output, flush=True)
    return output


def prepare():
    source = (ROOT / 'third_party/milkywayathome_client_196/nbody/src/nbody_mixeddwarf.c').read_text()
    for old, new in [('#include "nbody_king_model.h"', '#include "nbody_king_model.h"\n#include "quad_capture.h"'),
                     ('        unsigned int i = 0;', '        double s8_start = s8_capture_start();\n        unsigned int i = 0;'),
                     ('        /* pushing the bodies */',
                      '        s8_capture_end(s8_start, nbody, x, y, z, vx, vy, vz, masses);\n        /* pushing the bodies */')]:
        assert source.count(old) == 1
        source = source.replace(old, new)
    (BUILD / 'mixeddwarf-capture.c').write_bytes(source.encode())


def proof():
    harness.RUNS = RUNS
    binary = BUILD / 'x86-release/milkyway_nbody.exe'
    evidence = {}
    for case in ('small', 'medium', 'large', 'core-small'):
        reference = harness.copy_reference(case)
        run = harness.run(binary, case, 12, case + '-t12')
        evidence[case] = dict(threads=12, binary_sha256=sha(binary), run=relative(run),
                             reference=relative(reference), compare=exact(reference, run))
    capture = RUNS / 'initial-bodies.bin'
    harness.run(BUILD / 'x86-release/capture.exe', 'core-small', 12, 'core-small-capture',
                {'S8_INITIAL_BODIES': str(capture), 'S8_GENERATION_ONLY': '1'})
    sources = [ROOT.parent / 'S8-03/runs/s8-quad/off-12/initial-bodies.bin',
               ROOT.parent / 'S9-05/runs/s9-df/final-core/initial-bodies.bin']
    assert sha(capture) == '7117b750caad318ab42a781346ca480a9f43fa1828e0832b58ad06fc00b88b59'
    assert all(capture.read_bytes() == p.read_bytes() for p in sources)
    evidence['bodies'] = dict(capture=relative(capture), sources=list(map(str, sources)), sha256=sha(capture))
    print('PASS core-small bodies byte-identical to S8-03 and S9-05: ' + sha(capture), flush=True)
    identity = BUILD / 'x86-identity/milkyway_nbody.exe'
    run = harness.run(identity, 'large', 12, 'large-tree-identity-t12')
    exact(RUNS / 'large-reference', run)
    text = compare.captured_output(run)
    checks = re.findall(r'^TREE_IDENTITY step=(\d+).* PASS$', text, re.M)
    calls = int(re.search(r'^PHASE nbMakeTree \S+ (\d+)$', text, re.M)[1])
    assert list(map(int, checks)) == [0] + list(range(calls - 1))
    evidence['tree'] = dict(run=relative(run), binary_sha256=sha(identity), builds=calls, passes=len(checks))
    print('PASS large every-build tree identity: %d/%d' % (len(checks), calls), flush=True)
    harness.write_json(BUILD / 'proof.json', evidence)


def stage():
    lines = ['#!/usr/bin/env bash', '# Lead only: run inside an authorized card window.',
             'set -euo pipefail', 'cd "$(dirname "$0")/../.."', 'mkdir -p runs/card/s10']
    for case in ('large', 'core-small'):
        hist = 'OCS_data_2025_north_194.hist' if case == 'core-small' else 'input.hist'
        args = harness.arguments(case, 240)
        args[1], args[3] = 'params.lua', hist
        command = ['python', 'tools/card_run', '--benchmark', '--threads', '240', '--timeout', '900',
                   '--receipt', 'runs/card/s10/' + case + '.json',
                   '--file', 'build/s10/card-release-timers/milkyway_nbody.mic',
                   '--file', 'workunits/' + case + '/params.lua', '--file', 'workunits/' + case + '/' + hist]
        for runtime in sorted((ROOT / 'dist/card').glob('*.so*')):
            command += ['--file', relative(runtime)]
        command += ['scripts/card-launch-env.sh', 'OMP_NUM_THREADS=240', './milkyway_nbody.mic'] + args
        lines.append(' '.join(shlex.quote(v) for v in command) + ' > runs/card/s10/' + case + '.txt 2>&1')
    (BUILD / 'release-window.sh').write_bytes(('\n'.join(lines) + '\n').encode())
    files = [ROOT / p for p in ('config/release.env', 'mk/Makefile', 'mk/sources.mk',
             'scripts/build-release.sh', 'scripts/test-release.sh', 'scripts/s10-release.py',
             'scripts/package_card.sh', 'packaging/make_package.sh', 'scripts/card-launch-env.sh')]
    files += sorted((ROOT / 'patches').glob('*.patch'))
    # Freeze every patched translation unit/header as well as the patch inputs.

    for patch in sorted((ROOT / 'patches').glob('*.patch')):
        files += [ROOT / 'third_party/milkywayathome_client_196' / name
                  for name in re.findall(r'^\+\+\+ b/(\S+)', patch.read_text(), re.M)]
    for variant, program in (('card-release', 'milkyway_nbody.mic'), ('card-release-timers', 'milkyway_nbody.mic'),
                             ('x86-release', 'milkyway_nbody.exe'), ('x86-identity', 'milkyway_nbody.exe')):
        files += [BUILD / variant / name for name in (program, '.build-options')]
    files += list((ROOT / 'dist/milkyway_package').iterdir())
    files += [BUILD / 'x86-release/capture.exe', BUILD / 'mixeddwarf-capture.c', ROOT / 'tests/quad_capture.h',
              ROOT / 'tests/s9-df.mk', ROOT / 'tests/test_s10_release.py', ROOT / 'scripts/s8_integration.py',
              ROOT / 'scripts/compare.py']
    files += [p for p in RUNS.rglob('*') if p.is_file()]
    files += list((ROOT / 'dist/card').iterdir())
    files += [BUILD / 'release-window.sh', BUILD / 'proof.json', BUILD / 'proof.txt']
    files += list((ROOT / 'workunits').glob('*/*'))
    harness.write_json(BUILD / 'manifest.json', {relative(p): sha(p) for p in files if p.is_file()})
    print((BUILD / 'release-window.sh').read_text(), flush=True)


if __name__ == '__main__':
    {'prepare': prepare, 'proof': proof, 'stage': stage}[sys.argv[1]]()
