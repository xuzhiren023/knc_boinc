"""S9-05 evidence driver. Run through the bash entry points (Cygwin PATH)."""
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
BUILD = ROOT / 'build/s9/df'
RUNS = ROOT / 'runs/s9-df'
sys.path.insert(0, str(ROOT / 'scripts'))
import compare
ARGS = '4.90652 1 0.386382 0.20556 1.74668 0.0420765 46.125 15.623 -215.279 114.242 181.825 353270 1.21041 2.87629'.split()

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p, v):
    p.write_text(json.dumps(v, indent=2) + '\n')
def relative(p):
    return p.relative_to(ROOT).as_posix()
def experiment():
    folder = BUILD / 'experiment-tree'
    dest = folder / 'nbody/src/nbody_mixeddwarf.c'
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / 'third_party/milkywayathome_client_196/nbody/src/nbody_mixeddwarf.c', dest)
    header = folder / 'nbody/include/nbody_df_vector.h'
    header.unlink(missing_ok=True)
    for name in ('performance.patch', 'instrumentation.patch'):
        with (ROOT / 'probes/s9-df-vector' / name).open('rb') as source:
            subprocess.run(['patch', '--batch', '-p1', '-d', str(folder)], stdin=source, check=True)

def prepare():
    vector = len(sys.argv) > 2 and sys.argv[2] == '1'
    text = (BUILD / 'experiment-tree/nbody/src/nbody_mixeddwarf.c' if vector else
            ROOT / 'third_party/milkywayathome_client_196/nbody/src/nbody_mixeddwarf.c').read_text()
    text = text.replace('#include "nbody_king_model.h"', '#include "nbody_king_model.h"\n#include "quad_capture.h"')
    for a,b in [('        unsigned int i = 0;', '        double s8_start = s8_capture_start();\n        unsigned int i = 0;'),
                ('        /* pushing the bodies */', '        s8_capture_end(s8_start, nbody, x, y, z, vx, vy, vz, masses);\n        /* pushing the bodies */')]:
        assert text.count(a) == 1
        text = text.replace(a,b)
    (BUILD / 'mixeddwarf-capture.c').write_bytes(text.encode())
def run(variant, full=False, label=None):
    out = RUNS / ('full-final' if full else label or variant)
    out.mkdir(parents=True, exist_ok=True)
    exe = ROOT / 'build/s9' / ('x86-df' + variant) / 'capture.exe'
    if full:
        proof = json.loads((BUILD / 'vector-proof.json').read_text())
        exe = ROOT / 'build/s9' / ('x86-dfvector' if proof['kept'] else 'x86-dfreuse') / 'capture.exe'
        assert not (BUILD / 'full-started.json').exists(), 'Full generation already launched; inspect evidence before any rerun'
        save(BUILD / 'full-started.json', dict(binary=relative(exe), sha256=sha(exe), timestamp=time.time()))
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
    save(out / 'evidence.json', row)
    print(json.dumps(row, indent=2), flush=True)
    return row

def core():
    a = run('base')
    b = run('reuse')
    assert (ROOT / a['bodies']).read_bytes() == (ROOT / b['bodies']).read_bytes()
    assert a['likelihood_hex'] == b['likelihood_hex']
    assert compare.compare(RUNS / 'base', RUNS / 'reuse', compare.TOLERANCE) == 0
    ref = ROOT.parent / 'S8-09/runs/s8-09/final/core-small-bodies-reference.bin'
    assert (ROOT / b['bodies']).read_bytes() == ref.read_bytes()
    save(BUILD / 'core-proof.json', dict(base=a, reuse=b, reference=str(ref), reference_sha256=sha(ref)))
def vector():
    b = json.loads((BUILD / 'core-proof.json').read_text())['reuse']
    v = run('vector')
    assert (ROOT / v['bodies']).read_bytes() == (ROOT / b['bodies']).read_bytes()
    assert v['likelihood_hex'] == b['likelihood_hex']
    text = (RUNS / 'vector/stderr.txt').read_text()
    bodies, fallbacks = map(int, re.search(r'DF_VECTOR bodies=(\d+) fallbacks=(\d+)', text).groups())
    faster = v['generation_seconds'] < b['generation_seconds']
    save(BUILD / 'vector-proof.json', dict(bodies=bodies, fallbacks=fallbacks, generation_seconds=v['generation_seconds'],
         faster=faster, kept=faster and fallbacks < bodies / 2, capture=v['bodies'], likelihood_hex=v['likelihood_hex'],
         binary=v['binary'], binary_sha256=v['binary_sha256']))
def verify_final():
    row = run('reuse', label='final-core')
    proof = json.loads((BUILD / 'core-proof.json').read_text())
    assert (ROOT / row['bodies']).read_bytes() == (ROOT / proof['base']['bodies']).read_bytes()
    assert row['likelihood_hex'] == proof['base']['likelihood_hex']
    proof['final'] = row
    save(BUILD / 'core-proof.json', proof)

def reference():
    folder = ROOT.parent / 'S8-05/runs/s8-fastdf/full/checkpoint-reference'
    provenance = json.loads((folder / 'provenance.json').read_text())
    source = folder / 'initial-bodies.bin'
    assert provenance['source_commit'] == '1e640779f1cabf88aaa49e4db569cfe7e09016c4'
    assert sha(source) == provenance['initial_bodies_sha256']
    assert source.read_bytes() == (folder / 'x86-1-initial.bin').read_bytes()
    assert source.read_bytes() == (ROOT.parent / 'S8-09/runs/s8-09/final/full-117676-bodies-reference.bin').read_bytes()
    assert sha(ROOT / 'workunits/117676/params.lua') == provenance['params_sha256']
    save(BUILD / 'full-reference-provenance.json', provenance)

def full():
    reference()
    row = run('reuse', full=True)
    source = ROOT.parent / 'S8-09/runs/s8-09/final/full-117676-bodies-reference.bin'
    ref = BUILD / 'full-117676-reference.bin'
    shutil.copyfile(source, ref)
    assert (ROOT / row['bodies']).read_bytes() == ref.read_bytes()
    save(BUILD / 'full-proof.json', dict(capture=row['bodies'], reference=relative(ref), reference_source=str(source),
         sha256=sha(ref), binary=row['binary'], binary_sha256=row['binary_sha256'], generation_seconds=row['generation_seconds']))

def stage():
    proof = json.loads((BUILD / 'vector-proof.json').read_text())
    runtimes = BUILD / 'runtimes'
    runtimes.mkdir(exist_ok=True)
    out = ROOT / 'runs/card/s9-df'
    out.mkdir(parents=True, exist_ok=True)
    lines = ['#!/usr/bin/env bash', '# Lead only: inside an authorized card window.',
             'set -uo pipefail', 'cd "$(dirname "$0")/../../.."', 'mkdir -p runs/card/s9-df']
    variants = ['card-dfreuse'] + (['card-dfvec'] if proof['kept'] else [])
    for variant in variants:
        binary = ROOT / 'build/s9' / variant / 'milkyway_nbody.mic'
        label = variant + '-core-small-240'
        lines += ['# SHA256 ' + sha(binary),
                  '# Prediction: reuse removes 29 -> 15 samples/node; native gain is unmeasured.']
        cmd = ['python', 'tools/card_run', '--benchmark', '--threads', '240', '--timeout', '900',
               '--receipt', 'runs/card/s9-df/' + label + '.json',
               '--file', relative(binary), '--file', 'workunits/core-small/params.lua',
               '--file', 'workunits/core-small/OCS_data_2025_north_194.hist']
        for name in ('libgomp.so.1', 'libstdc++.so.6', 'libgcc_s.so.1'):
            cmd += ['--file', 'build/s9/df/runtimes/' + name]
        cmd += ['scripts/card-launch.sh', 'OMP_NUM_THREADS=240', '-f', 'params.lua',
                '-h', 'OCS_data_2025_north_194.hist', '--seed', '65477096', '--nthreads', '240',
                '--print-histogram', '--ignore-checkpoint', '--checkpoint-interval=-1', '-np', '14', '-p'] + ARGS
        lines += [' '.join(shlex.quote(v) for v in cmd) + ' > runs/card/s9-df/' + label + '.txt 2>&1',
                  'status=$?', 'echo "$status" > runs/card/s9-df/' + label + '.exit',
                  '[[ $status == 0 ]] || exit "$status"']
    (BUILD / 'card-commands.sh').write_bytes((chr(10).join(lines) + chr(10)).encode())
    files = [ROOT / 'mk/Makefile', ROOT / 'mk/sources.mk', ROOT / 'scripts/build-s9-df.sh',
             ROOT / 'third_party/milkywayathome_client_196/nbody/src/nbody_mixeddwarf.c']
    files += list((ROOT / 'patches').glob('*.patch'))
    files += [runtimes / name for name in ('libgomp.so.1', 'libstdc++.so.6', 'libgcc_s.so.1')]
    for variant in variants:
        files += [ROOT / 'build/s9' / variant / name for name in ('milkyway_nbody.mic', '.build-options', 'knc-lint.txt')]
    save(BUILD / 'handoff-manifest.json', {relative(p): sha(p) for p in files})
    print((BUILD / 'card-commands.sh').read_text(), flush=True)

if __name__ == '__main__':
    os.chdir(ROOT)
    BUILD.mkdir(parents=True, exist_ok=True)
    RUNS.mkdir(parents=True, exist_ok=True)
    globals()[sys.argv[1]]()
