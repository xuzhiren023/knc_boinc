"""S10-05 offline evidence driver; invoke through the bash entry points."""
import datetime
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
B = ROOT / 'build/s10/df-special'
RUNS = ROOT / 'runs/s10-df-special'
import compare
ARGS = '4.90652 1 0.386382 0.20556 1.74668 0.0420765 46.125 15.623 -215.279 114.242 181.825 353270 1.21041 2.87629'.split()

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def save(p, v):
    p.write_text(json.dumps(v, indent=2) + '\n')

def rel(p):
    return p.relative_to(ROOT).as_posix()

def prepare(variant):
    shared = Path('C:/Users/xuzhi/Documents/gcc_knc/.work/_shared')
    card = shared / 'gcc-knc-16.2.0/lib/gcc/k1om-mpss-linux/16.2.0/libknc_vmath.a'
    snapshot = shared / 'S10-02/knc/libknc_vmath.a'
    host = shared / 'S10-02/host/libknc_vmath.a'
    assert sha(card) == sha(snapshot) == 'fc732e6f48b7a4bae49eeb32fe9fd78f730e10597b83cfe0495aca150fc4f786'
    (B / 'library-provenance.txt').write_text(
        'Installed card archive matches S10-02/knc exactly: ' + sha(card) + '\n' +
        'Matching S10-02/host archive: ' + sha(host) + '\n' +
        'Host/card numerical agreement still requires the card window.\n')
    u = ROOT / 'third_party/milkywayathome_client_196'
    tree = B / (variant + '-tree')
    for name in ('nbody/src/nbody_mixeddwarf.c', 'nbody/include/nbody_df_special.h', 'nbody/include/nbody_gen_profile.h'):
        dest = tree / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(u / name, dest)
    if variant == 'vmath':
        with (ROOT / 'probes/s10-df-vmath/performance.patch').open('rb') as source:
            subprocess.run(['patch', '--batch', '-p1', '-d', str(tree)], stdin=source, check=True)
    source = (tree / 'nbody/src/nbody_mixeddwarf.c').read_text()
    for a, b in [('#include "nbody_king_model.h"', '#include "nbody_king_model.h"\n#include "s10_df_capture.h"'),
                 ('        unsigned int i = 0;', '        double s8_start = s8_capture_start();\n        s10_rng_open();\n        unsigned int i = 0;'),
                 ('            GP_BODY_END();', '            s10_rng_body(prng);\n            GP_BODY_END();'),
                 ('        /* pushing the bodies */', '        s10_rng_close();\n        s8_capture_end(s8_start, nbody, x, y, z, vx, vy, vz, masses);\n        /* pushing the bodies */')]:
        assert source.count(a) == 1, a
        source = source.replace(a, b)
    (B / (variant + '-capture.c')).write_bytes(source.encode())
    shutil.copyfile(u / 'nbody/include/nbody_gen_profile.h', B / 'nbody_gen_profile.h')

def run(variant, full=False):
    label = ('full-' if full else 'core-') + variant
    out = RUNS / label
    out.mkdir(parents=True, exist_ok=True)
    exe = B / ('x86-' + variant) / 'capture.exe'
    if full:
        marker = B / (label + '-started.json')
        assert not marker.exists(), 'Full generation already launched; do not repeat: ' + label
        save(marker, dict(binary=rel(exe), binary_sha256=sha(exe), timestamp=time.time()))
    case = '117676' if full else 'core-small'
    cmd = [str(exe), '-f', str(ROOT / ('workunits/' + case + '/params.lua')),
           '-h', str(ROOT / 'workunits/core-small/OCS_data_2025_north_194.hist'),
           '-z', str(out / 'histogram.txt'), '-c', str(out / 'checkpoint'),
           '--seed', '65477096', '--nthreads', '12', '--print-histogram',
           '--ignore-checkpoint', '--checkpoint-interval=-1', '-np', '14', '-p'] + ARGS
    env = dict(os.environ, OMP_NUM_THREADS='12', OMP_DYNAMIC='FALSE',
               S8_INITIAL_BODIES=str(out / 'initial-bodies.bin'), S10_RNG_TRACE=str(out / 'rng.bin'))
    if full:
        env['S8_GENERATION_ONLY'] = '1'
    save(out / 'command.json', cmd)
    t = time.monotonic()
    with (out / 'stdout.txt').open('w') as stdout, (out / 'stderr.txt').open('w') as stderr:
        result = subprocess.run(cmd, cwd=out, env=env, stdout=stdout, stderr=stderr)
    seconds = time.monotonic() - t
    (out / 'exit.txt').write_text(str(result.returncode) + '\n')
    assert result.returncode == 0, (label, result.returncode)
    text = (out / 'stderr.txt').read_text()
    row = dict(binary=rel(exe), binary_sha256=sha(exe), threads=12, run=rel(out),
               generation_seconds=float(re.search(r'S8_GENERATION_SECONDS=([\d.]+)', text)[1]),
               whole_seconds=seconds, rng_record_bytes=int(re.search(r'S10_RNG_RECORD_BYTES=(\d+)', text)[1]))
    if not full:
        row['likelihood_hex'] = compare.load_run(out)[0].hex()
    save(B / (label + '.json'), row)
    print(json.dumps(row, indent=2), flush=True)
    return row

def exact():
    a, b = (json.loads((B / ('core-' + v + '.json')).read_text()) for v in ('release', 'special'))
    ar, br = ROOT / a['run'], ROOT / b['run']
    assert (ar / 'initial-bodies.bin').read_bytes() == (br / 'initial-bodies.bin').read_bytes()
    assert sha(ar / 'initial-bodies.bin') == '7117b750caad318ab42a781346ca480a9f43fa1828e0832b58ad06fc00b88b59'
    assert (ar / 'rng.bin').read_bytes() == (br / 'rng.bin').read_bytes()
    assert a['likelihood_hex'] == b['likelihood_hex']
    assert compare.compare(ar, br, compare.TOLERANCE) == 0
    p = json.loads((B / 'kernel.json').read_text())
    assert p['kernel_mismatches'] == 0 and p['unsupported_models_original']
    p.update(reference=rel(ar), special=rel(br), likelihood_hex=a['likelihood_hex'])
    save(B / 'exact-proof.json', p)


def file_differences(a, b, width):
    assert a.stat().st_size == b.stat().st_size and a.stat().st_size % width == 0
    count, first, index = 0, None, 0
    with a.open('rb') as aa, b.open('rb') as bb:
        while True:
            x, y = aa.read(width), bb.read(width)
            if not x:
                break
            if x != y:
                count += 1
                if first is None:
                    first = index
            index += 1
    return count, first


def differences():
    result = {}
    for case, prefix, reference in (('core-small', 'core-', 'release'), ('117676', 'full-', 'special')):
        a, b = (json.loads((B / (prefix + v + '.json')).read_text()) for v in (reference, 'vmath'))
        ar, br = ROOT / a['run'], ROOT / b['run']
        n, first = file_differences(ar / 'initial-bodies.bin', br / 'initial-bodies.bin', 56)
        assert a['rng_record_bytes'] == b['rng_record_bytes']
        nr, firstr = file_differences(ar / 'rng.bin', br / 'rng.bin', a['rng_record_bytes'])
        row = dict(reference=rel(ar), experiment=rel(br), different_bodies=n, first_different_body=first,
                   different_rng_states=nr, first_rng_divergence_body=firstr, rng_record_bytes=a['rng_record_bytes'],
                   indexing='zero based; RNG state recorded at end of body, before CM correction')
        if case == 'core-small':
            x, y = (compare.load_run(d)[0] for d in (ar, br))
            row.update(exact_likelihood_hex=x.hex(), experiment_likelihood_hex=y.hex(), likelihood_difference=y-x)
        else:
            assert sha(ar / 'initial-bodies.bin') == 'd09e23bcd50852add7f7bea4f8c9e68f6d18e4d39b2a302503d4bceaad23209f'
        result[case] = row
    save(B / 'differences.json', result)
    print(json.dumps(result, indent=2), flush=True)


def stage():
    # Card predictions are explicitly unmeasured hypotheses; twin support and
    # compiler diagnostics are frozen beside this script before the window.
    prediction = ('Exact: dispatch removal should reduce the 34.3 s node phase, but scalar crlibm and gamma remain; '
                  'predict 0-10% setup improvement from 47.7 s (43-48 s). '
                  'VMATH: lane-core call/mask overhead can dominate; predict no reliable speed win '
                  '(40-65 s setup). Native measurements decide; these are uncalibrated hypotheses.')
    lines = ['#!/usr/bin/env bash', '# Lead only: inside an authorized card window.',
             'set -euo pipefail', 'cd "$(dirname "$0")/../../.."', 'mkdir -p runs/card/s10-df-special',
             '# Prediction: ' + prediction]
    for variant in ('release', 'special', 'vmath'):
        exe = B / ('card-' + variant) / 'milkyway_nbody.mic'
        label = variant + '-core-small-240'
        lines += ['# SHA256 ' + sha(exe)]
        cmd = ['python', 'tools/card_run', '--benchmark', '--threads', '240', '--timeout', '900',
               '--receipt', 'runs/card/s10-df-special/' + label + '.json', '--file', rel(exe),
               '--file', 'workunits/core-small/params.lua',
               '--file', 'workunits/core-small/OCS_data_2025_north_194.hist']
        for runtime in sorted((B / 'runtimes').iterdir()):
            cmd += ['--file', rel(runtime)]
        cmd += ['scripts/card-launch-env.sh', 'OMP_NUM_THREADS=240', './milkyway_nbody.mic',
                '-f', 'params.lua', '-h', 'OCS_data_2025_north_194.hist', '--seed', '65477096',
                '--nthreads', '240', '--print-histogram', '--ignore-checkpoint',
                '--checkpoint-interval=-1', '-np', '14', '-p'] + ARGS
        lines += [' '.join(shlex.quote(x) for x in cmd) + ' > runs/card/s10-df-special/' + label + '.txt 2>&1']
    lines += ['python scripts/s10-df-special.py card_report']
    (B / 'card-window.sh').write_bytes(('\n'.join(lines) + '\n').encode())
    files = [ROOT / p for p in ('mk/Makefile', 'mk/sources.mk', 'config/release.env',
             'scripts/build-s10-df-special.sh', 'scripts/s10-df-special.py', 'scripts/test-s10-df-special.sh',
             'tests/s10-df-special.mk', 'tests/s10_df_capture.h', 'tests/s10_df_special_kernel.c',
             'tests/test_s10_df_special.py', 'probes/s10-df-vmath/performance.patch',
             'probes/s10_df_vmath_repro.c', 'docs/research/s10-df-special.md',
             'patches/zzzzzz-nbody-df-special.patch')]
    files += list((B / 'runtimes').iterdir())
    files += [B / p for p in ('card-window.sh', 'exact-proof.json', 'differences.json', 'library-provenance.txt',
             'kernel.json', 'vmath-kernel.json', 'card-special-vec.txt', 'card-vmath-vec.txt')]
    for variant in ('release', 'special', 'vmath'):
        files += [B / ('card-' + variant) / p for p in ('milkyway_nbody.mic', '.build-options', 'knc-lint.txt')]
        files += [B / ('x86-' + variant) / p for p in ('capture.exe', '.build-options')]
        files += [B / ('core-' + variant + '.json')]
    for p in RUNS.rglob('*'):
        if p.is_file():
            files.append(p)
    save(B / 'handoff.json', dict(prediction=prediction,
         prediction_recorded_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
         files={rel(p): sha(p) for p in files}))


def card_report():
    folder = ROOT / 'runs/card/s10-df-special'
    values = {}
    for variant in ('release', 'special', 'vmath'):
        label = variant + '-core-small-240'
        likelihood = compare.load_run(folder / (label + '.txt'))[0]
        receipt = json.loads((folder / (label + '.json')).read_text())
        assert receipt['exit_code'] == 0
        values[variant] = dict(likelihood=likelihood, likelihood_hex=likelihood.hex(),
                               receipt=rel(folder / (label + '.json')),
                               card_seconds=60 * receipt['card_minutes'])
    assert values['release']['likelihood_hex'] == values['special']['likelihood_hex']
    values['vmath']['likelihood_difference'] = values['vmath']['likelihood'] - values['release']['likelihood']
    save(folder / 'summary.json', values)
    print(json.dumps(values, indent=2))


if __name__ == '__main__':
    os.chdir(ROOT)
    B.mkdir(parents=True, exist_ok=True)
    globals()[sys.argv[1]](*sys.argv[2:])
