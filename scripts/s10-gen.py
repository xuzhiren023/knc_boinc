"""S10-03 evidence driver. Run through the bash entry points (Cygwin PATH)."""
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import time
ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'build/s10/gen'
RUNS = ROOT / 'runs/s10-gen'
sys.path.insert(0, str(ROOT / 'scripts'))
import compare
ARGS = '4.90652 1 0.386382 0.20556 1.74668 0.0420765 46.125 15.623 -215.279 114.242 181.825 353270 1.21041 2.87629'.split()

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p, v):
    p.write_text(json.dumps(v, indent=2) + '\n')
def relative(p):
    return p.relative_to(ROOT).as_posix()
def prepare():
    text = (ROOT / 'third_party/milkywayathome_client_196/nbody/src/nbody_mixeddwarf.c').read_text()
    text = text.replace('#include "nbody_king_model.h"', '#include "nbody_king_model.h"\n#include "quad_capture.h"')
    for a,b in [('        unsigned int i = 0;', '        double s8_start = s8_capture_start();\n        unsigned int i = 0;'),
                ('        /* pushing the bodies */', '        s8_capture_end(s8_start, nbody, x, y, z, vx, vy, vz, masses);\n        /* pushing the bodies */')]:
        assert text.count(a) == 1
        text = text.replace(a,b)
    shutil.copyfile(ROOT / 'third_party/milkywayathome_client_196/nbody/include/nbody_gen_profile.h', BUILD / 'nbody_gen_profile.h')
    (BUILD / 'mixeddwarf-capture.c').write_bytes(text.encode())
def run(variant, full=False, label=None):
    out = RUNS / ('full-final' if full else label or variant)
    out.mkdir(parents=True, exist_ok=True)
    exe = ROOT / 'build/s10' / variant / 'capture.exe'
    if full:
        exe = ROOT / 'build/s10/selected/capture.exe'
        assert not (BUILD / 'full-started.json').exists(), 'Full generation already launched; inspect evidence before any rerun'
        with (BUILD / 'full-started.json').open('x') as guard:
            json.dump(dict(binary=relative(exe), binary_sha256=sha(exe), timestamp=time.time()), guard, indent=2)
    lua = ROOT / ('workunits/117676/params.lua' if full else 'workunits/core-small/params.lua')
    hist = ROOT / 'workunits/core-small/OCS_data_2025_north_194.hist'
    cmd = [str(exe), '-f', str(lua), '-h', str(hist), '-z', str(out / 'histogram.txt'), '-c', str(out / 'checkpoint'),
           '--seed', '65477096', '--nthreads', '12', '--print-histogram', '--ignore-checkpoint', '--checkpoint-interval=-1', '-np','14','-p'] + ARGS
    env = dict(os.environ, OMP_NUM_THREADS='12', OMP_DYNAMIC='FALSE', S8_INITIAL_BODIES=str(out / 'initial-bodies.bin'))
    if full:
        env['S8_GENERATION_ONLY'] = '1'
    save(out / 'command.json', cmd)
    t = time.monotonic()
    with (out / 'stdout.txt').open('w') as stdout, (out / 'stderr.txt').open('w') as stderr:
        result = subprocess.run(cmd, cwd=out, env=env, stdout=stdout, stderr=stderr)
    (out / 'exit.txt').write_text(str(result.returncode) + '\n')
    assert result.returncode == 0, (variant, result.returncode)
    text = (out / 'stderr.txt').read_text()
    row = dict(binary=relative(exe), binary_sha256=sha(exe), threads=12,
               generation_seconds=float(re.search(r'S8_GENERATION_SECONDS=([\d.]+)',text)[1]),
               whole_seconds=time.monotonic()-t, bodies=relative(out / 'initial-bodies.bin'))
    if not full:
        row['likelihood_hex'] = compare.load_run(out)[0].hex()
    if 'GEN_PROFILE bodies=' in text:
        line = re.search(r'GEN_PROFILE (.*)', text)[1]
        profile = {k: float(v) if k.endswith('seconds') else int(v)
                   for k,v in re.findall(r'(\w+)=([\d.]+)', line)}
        profile['exclusive'] = {}
        profile['inclusive'] = {}
        for phase, exclusive, inclusive in re.findall(r'GEN_PHASE (\w+) exclusive=([\d.]+) inclusive=([\d.]+)', text):
            profile['exclusive'][phase] = float(exclusive)
            profile['inclusive'][phase] = float(inclusive)
        profile['per_body'] = {k: {'min':int(lo),'max':int(hi),'mean':profile[k]/profile['bodies']}
            for k,lo,hi in re.findall(r'GEN_PER_BODY (\w+) min=(\d+) max=(\d+)',text)}
        save(BUILD / (variant + '.json'), profile)
    save(out / 'evidence.json', row)
    print(json.dumps(row, indent=2), flush=True)
    return row


def core():
    reference = RUNS / 'reference'
    reference.mkdir(exist_ok=True)
    source = ROOT.parent / 'S9-05/runs/s9-df/reuse'
    for name in ('initial-bodies.bin','histogram.txt','stderr.txt','stdout.txt','exit.txt'):
        shutil.copyfile(source / name, reference / name)
    assert sha(reference / 'initial-bodies.bin') == '7117b750caad318ab42a781346ca480a9f43fa1828e0832b58ad06fc00b88b59'
    p = dict(reference=relative(reference / 'initial-bodies.bin'), likelihood_hex=compare.load_run(reference)[0].hex())
    for label in ('base-profile','selected-profile','selected'):
        row = json.loads((RUNS / label / 'evidence.json').read_text())
        assert (ROOT / row['bodies']).read_bytes() == (reference / 'initial-bodies.bin').read_bytes()
        assert row['likelihood_hex'] == p['likelihood_hex']
        assert compare.compare(reference, RUNS / label, compare.TOLERANCE) == 0
        assert compare.load_run(reference) == compare.load_run(RUNS / label)
        p[label] = row
    save(BUILD / 'core-proof.json', p)

def full():
    source = ROOT.parent / 'S8-05/runs/s8-fastdf/full/checkpoint-reference'
    provenance = json.loads((source / 'provenance.json').read_text())
    assert provenance['source_commit'] == '1e640779f1cabf88aaa49e4db569cfe7e09016c4'
    assert provenance['params_sha256'] == sha(ROOT / 'workunits/117676/params.lua')
    assert provenance['initial_bodies_sha256'] == sha(source / 'initial-bodies.bin')
    assert (source / 'initial-bodies.bin').read_bytes() == (source / 'x86-1-initial.bin').read_bytes()
    reference = BUILD / 'full-reference.bin'
    shutil.copyfile(source / 'initial-bodies.bin', reference)
    save(BUILD / 'full-reference-provenance.json', provenance)
    row = run('selected', full=True)
    assert (ROOT / row['bodies']).read_bytes() == reference.read_bytes()
    row['reference'] = relative(reference)
    save(BUILD / 'full-proof.json', row)


def select():
    baseline = json.loads((BUILD / 'base-profile.json').read_text())
    candidate = json.loads((BUILD / 'selected-profile.json').read_text())
    root_share = baseline['exclusive']['dist_serial'] / (baseline['total_seconds'] - baseline['exclusive']['nodes'])
    prediction = ('Baseline setup 46.9 s: node team 30, root/search 15, serial quad 1.5, other 0.4; '
        'GEN_PIPELINE setup 39 s (35..50), caller root/search 3..5, node/team 30..43. '
        'Two preparation workers reserved; native gain unproven; host candidate slower.')
    save(BUILD / 'selection.json', dict(option='GEN_PIPELINE=1', baseline=baseline, candidate=candidate,
        serial_root_fraction=root_share,
        justification='Root/search is the largest serial phase outside node evaluation. '
        'Overlap both exact next golden-section branch preparations in the current node team; '
        'preserve original decisions and RNG. Host root/search falls but generation slows; '
        'retain as an off-by-default card experiment, not a measured release speedup.', prediction=prediction))

def stage():
    from datetime import datetime, timezone
    prediction = json.loads((BUILD / 'selection.json').read_text())['prediction']
    files = []
    lines = ['#!/usr/bin/env bash', '# Lead only: in an authorized card window.',
             'set -euo pipefail', 'cd "$(dirname "$0")/../../.."', 'mkdir -p runs/card/s10-gen',
             '# Prediction: ' + prediction]
    for variant in ('card-profile','card-selected'):
        binary = ROOT / 'build/s10' / variant / 'milkyway_nbody.mic'
        label = variant + '-core-small-240'
        cmd = ['python','tools/card_run','--benchmark','--threads','240','--timeout','900',
               '--receipt','runs/card/s10-gen/' + label + '.json', '--file',relative(binary),
               '--file','workunits/core-small/params.lua','--file','workunits/core-small/OCS_data_2025_north_194.hist']
        for name in ('libgomp.so.1','libstdc++.so.6','libgcc_s.so.1'):
            cmd += ['--file','build/s10/gen/runtimes/' + name]
        cmd += ['scripts/card-launch.sh','OMP_NUM_THREADS=240','-f','params.lua',
                '-h','OCS_data_2025_north_194.hist','--seed','65477096','--nthreads','240',
                '--print-histogram','--ignore-checkpoint','--checkpoint-interval=-1','-np','14','-p'] + ARGS
        lines += ['# Binary SHA256: ' + sha(binary), 'set +e',
                  ' '.join(shlex.quote(v) for v in cmd) + ' > runs/card/s10-gen/' + label + '.txt 2>&1',
                  'status=$?', 'set -e', 'echo "$status" > runs/card/s10-gen/' + label + '.exit',
                  '[[ $status == 0 ]] || exit "$status"']
    (BUILD / 'card-window.sh').write_bytes((chr(10).join(lines)+chr(10)).encode())
    for variant in ('card-profile','card-selected','card-selected-clean'):
        files += [ROOT / 'build/s10' / variant / name for name in ('milkyway_nbody.mic','.build-options','knc-lint.txt')]
    files += list((BUILD / 'runtimes').glob('*'))
    files += list((ROOT / 'patches').glob('*.patch'))
    files += [ROOT / name for name in ('mk/Makefile','mk/sources.mk','scripts/build-s10-gen.sh',
        'scripts/s10-gen.py','scripts/test-s10-gen.sh','tests/s10-gen.mk','tests/quad_capture.h','tests/test_s10_gen.py',
        'third_party/milkywayathome_client_196/nbody/src/nbody_mixeddwarf.c',
        'third_party/milkywayathome_client_196/nbody/include/nbody_gen_profile.h',
        'docs/research/s10-gen.md','patches/README.md','workunits/core-small/params.lua',
        'workunits/core-small/OCS_data_2025_north_194.hist','scripts/card-launch.sh','tools/card_run')]
    files += [BUILD / name for name in ('selection.json','core-proof.json','full-proof.json','card-window.sh')]
    save(BUILD / 'handoff.json', dict(prediction_recorded_utc=datetime.now(timezone.utc).isoformat(),
        files={relative(f):sha(f) for f in files}))


if __name__ == '__main__':
    os.chdir(ROOT)
    BUILD.mkdir(parents=True, exist_ok=True)
    RUNS.mkdir(parents=True, exist_ok=True)
    if sys.argv[1] == 'run':
        run(sys.argv[2])
    else:
        globals()[sys.argv[1]]()
