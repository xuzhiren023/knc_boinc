"""Reproducible S8-09 build provenance, exact host proof and lead-only jobs."""
import argparse
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
BUILD = ROOT / 'build/s8-09'
RUNS = ROOT / 'runs/s8-09/final'
ARGS = '4.90652 1 0.386382 0.20556 1.74668 0.0420765 46.125 15.623 -215.279 114.242 181.825 353270 1.21041 2.87629'.split()
sys.path.insert(0, str(ROOT / 'scripts'))
import compare


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')


def manifest():
    files = [ROOT / 'mk/Makefile', ROOT / 'mk/sources.mk', ROOT / 'config/s8-09.env']
    files += sorted((ROOT / 'patches').glob('*.patch'))
    files += sorted((ROOT / 'workunits').glob('*/*'))
    value = {str(p.relative_to(ROOT)): sha(p) for p in files if p.is_file()}
    for patch in sorted((ROOT / 'patches').glob('*.patch')):
        for name in re.findall(r'^\+\+\+ b/(\S+)', patch.read_text(), re.M):
            source = ROOT / 'third_party/milkywayathome_client_196' / name
            value['source/' + name] = sha(source)
    for target, name in (('x86-final', 'milkyway_nbody.exe'), ('card', 'milkyway_nbody.mic')):
        value['build/s8-09/' + target + '/' + name] = sha(BUILD / target / name)
    write_json(BUILD / 'manifest.json', value)


def arguments(case, threads):
    args = ['-f', 'workunits/' + case + '/params.lua', '-h',
            'workunits/' + case + '/' + ('OCS_data_2025_north_194.hist' if case == 'core-small' else 'input.hist'),
            '--seed', '65477096' if case == 'core-small' else '670828913', '--nthreads', str(threads),
            '--print-histogram', '--ignore-checkpoint', '--checkpoint-interval=-1']
    return args + (['-np', '14', '-p'] + ARGS if case == 'core-small' else
                   [str(dict(small=64, medium=1024, large=20000)[case])])


def run(exe, case, threads, label, extra_env=None, full=False):
    out = RUNS / label
    out.mkdir(parents=True, exist_ok=True)
    for name in ('stdout.txt', 'stderr.txt', 'histogram.txt', 'exit.txt', 'seconds.txt'):
        (out / name).unlink(missing_ok=True)
    args = arguments(case, threads)
    if full:
        args[1] = 'workunits/117676/params.lua'
    # The stock BOINC app opens stderr.txt in its working directory. Isolate
    # every run and resolve input paths before changing that directory.
    for option in ('-f', '-h'):
        index = args.index(option) + 1
        args[index] = str(ROOT / args[index])
    cmd = [str(exe), '-z', str(out / 'histogram.txt'), '-c', str(out / 'checkpoint')] + args
    write_json(out / 'command.json', cmd)
    env = dict(os.environ, OMP_DYNAMIC='FALSE', OMP_NUM_THREADS=str(threads))
    env.update(extra_env or {})
    start = time.monotonic()
    with (out / 'stdout.txt').open('w') as stdout, (out / 'stderr.txt').open('w') as stderr:
        result = subprocess.run(cmd, cwd=out, env=env, stdout=stdout, stderr=stderr)
    (out / 'seconds.txt').write_text('%.6f\n' % (time.monotonic() - start))
    (out / 'exit.txt').write_text(str(result.returncode) + '\n')
    if result.returncode:
        raise RuntimeError('%s failed (%s); see stderr.txt' % (label, result.returncode))
    print('PASS completed %s (%s s)' % (label, (out / 'seconds.txt').read_text().strip()), flush=True)
    return out


def copy_reference(case):
    source = (ROOT.parent / 'S8-03/runs/s8-quad/off-12' if case == 'core-small' else
              ROOT.parent / 'S7-01/runs/force-chunk' / (case + '-chunk196-default-t12'))
    dest = RUNS / (case + '-reference')
    dest.mkdir(parents=True, exist_ok=True)
    for name in ('stdout.txt', 'stderr.txt', 'histogram.txt', 'exit.txt', 'seconds.txt'):
        if (dest / name).exists():
            assert (source / name).read_bytes() == (dest / name).read_bytes(), 'retained reference changed: ' + str(source)
        else:
            shutil.copyfile(source / name, dest / name)
    write_json(dest / 'provenance.json', {str(p): sha(p) for p in source.iterdir()
                                         if p.name in ('stdout.txt', 'stderr.txt', 'histogram.txt')})
    return dest


def capture_build():
    source = (ROOT / 'third_party/milkywayathome_client_196/nbody/src/nbody_mixeddwarf.c').read_text()
    source = source.replace('#include "nbody_king_model.h"',
                            '#include "nbody_king_model.h"\n#include "quad_capture.h"')
    for marker, replacement in [('        unsigned int i = 0;',
                                '        double s8_start = s8_capture_start();\n        unsigned int i = 0;'),
                               ('        /* pushing the bodies */',
                                '        s8_capture_end(s8_start, nbody, x, y, z, vx, vy, vz, masses);\n        /* pushing the bodies */')]:
        assert source.count(marker) == 1
        source = source.replace(marker, replacement)
    (BUILD / 'mixeddwarf-capture.c').write_text(source)
    with (BUILD / 'capture-build.log').open('w') as log:
        subprocess.run(['make', '-C', 'mk', '-f', '../tests/s8-capture.mk', '-j4',
                        'TARGET=x86', 'OUT=../build/s8-09/x86-final', 's8-capture'],
                       check=True, stdout=log, stderr=subprocess.STDOUT)


def bodies(full):
    capture_build()
    exe = BUILD / 'x86-final/capture.exe'
    core = RUNS / 'core-small-bodies-final.bin'
    run(exe, 'core-small', 12, 'core-small-capture', {'S8_INITIAL_BODIES': str(core)})
    reference = ROOT.parent / 'S8-03/runs/s8-quad/off-12/initial-bodies.bin'
    shutil.copyfile(reference, RUNS / 'core-small-bodies-reference.bin')
    assert core.read_bytes() == reference.read_bytes(), 'core-small generated bodies changed'
    if not full:
        return
    # S8-05 recovers initial body rows from two independent S7-02 step-one
    # checkpoints, checking source provenance and equality. Keep that evidence.
    reference = ROOT.parent / 'S8-05/runs/s8-fastdf/full/checkpoint-reference'
    source = reference / 'initial-bodies.bin'
    provenance = json.loads((reference / 'provenance.json').read_text())
    assert provenance['source_commit'] == '1e640779f1cabf88aaa49e4db569cfe7e09016c4'
    assert sha(source) == provenance['initial_bodies_sha256']
    assert source.read_bytes() == (reference / 'x86-1-initial.bin').read_bytes()
    params = ROOT.parent / 'S7-02/runs/real/x86-12/nbody_parameters.lua'
    assert sha(params) == provenance['params_sha256']
    dest = ROOT / 'workunits/117676'
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(params, dest / 'params.lua')
    shutil.copyfile(source, RUNS / 'full-117676-bodies-reference.bin')
    write_json(RUNS / 'full-117676-reference-provenance.json', provenance)
    final = RUNS / 'full-117676-bodies-final.bin'
    run(exe, 'core-small', 12, 'full-117676-capture',
        {'S8_INITIAL_BODIES': str(final), 'S8_GENERATION_ONLY': '1'}, full=True)
    assert source.read_bytes() == final.read_bytes(), 'full 117676 generated bodies changed'


def matrix():
    references = {}
    for case in ('small', 'medium', 'large', 'core-small'):
        ref = copy_reference(case)
        references[case] = str(ref.relative_to(ROOT))
        for threads in (1, 4, 12):
            out = run(BUILD / 'x86-final/milkyway_nbody.exe', case, threads, '%s-t%d' % (case, threads))
            assert compare.compare(ref, out, compare.TOLERANCE) == 0
            assert compare.load_run(ref) == compare.load_run(out), 'exact science mismatch'
    write_json(BUILD / 'release-matrix.json', dict(references=references,
               binary_sha256=sha(BUILD / 'x86-final/milkyway_nbody.exe')))
    return references


def proof(full):
    references = matrix()
    bodies(full)
    tree_changed = os.environ.get('TREE_VARIANT', '0') != '0'
    if tree_changed:
        with (BUILD / 'tree-check-build.log').open('w') as log:
            subprocess.run(['make', '-C', 'mk', '-f', '../tests/s8-capture.mk', '-j4',
                            'TARGET=x86', 'OUT=../build/s8-09/x86-final', 's8-tree-check'],
                           check=True, stdout=log, stderr=subprocess.STDOUT)
        for case in ('small', 'medium', 'large', 'core-small'):
            for threads in (1, 4, 12):
                out = run(BUILD / 'x86-final/tree-check.exe', case, threads,
                          'tree-%s-t%d' % (case, threads))
                assert compare.compare(ROOT / references[case], out, compare.TOLERANCE) == 0
    write_json(BUILD / 'proof.json', dict(references=references,
               binary_sha256=sha(BUILD / 'x86-final/milkyway_nbody.exe'), tree_changed=tree_changed))


def stock():
    source = ROOT.parent / 'S7-02/runs/real/inputs/milkyway_nbody_1.96_windows_x86_64__mt.exe'
    dest = BUILD / 'stock-196.exe'
    shutil.copyfile(source, dest)
    write_json(BUILD / 'stock-provenance.json', dict(source=str(source), sha256=sha(dest)))
    for case in ('large', 'core-small'):
        out = run(dest, case, 12, 'stock-' + case)
        ref = copy_reference(case)
        assert compare.compare(ref, out, compare.TOLERANCE) == 0
        assert compare.load_run(ref)[0].hex() == compare.load_run(out)[0].hex()


def quick():
    for case in ('large', 'core-small'):
        out = run(BUILD / 'x86-final/milkyway_nbody.exe', case, 12, 'quick-' + case)
        ref = copy_reference(case)
        assert compare.compare(ref, out, compare.TOLERANCE) == 0
        assert compare.load_run(ref) == compare.load_run(out)


def import_card(number):
    """Import only successful, exact native outputs for the frozen final binary."""
    frozen = BUILD / ('batch-%d' % number)
    binary_hash = sha(frozen / 'milkyway_nbody.mic')
    manifest = json.loads((frozen / 'manifest.json').read_text())
    assert manifest['build/s8-09/card/milkyway_nbody.mic'] == binary_hash
    assert sha(BUILD / 'card/milkyway_nbody.mic') == binary_hash, 'batch is not the current final binary'
    evidence = {}
    for case in ('large', 'core-small'):
        label = 'batch-%d-%s-240' % (number, case)
        folder = ROOT / 'runs/card/s8-09'
        receipt_path = folder / (label + '.json')
        receipt = json.loads(receipt_path.read_text())
        assert receipt['result_class'] == 'program'
        assert receipt['exit_code'] == receipt['program_exit_code'] == 0
        output = folder / (label + '.txt')
        reference = copy_reference(case)
        assert compare.compare(reference, output, compare.TOLERANCE) == 0
        assert compare.load_run(reference) == compare.load_run(output)
        phase = {name: dict(seconds=float(seconds), calls=int(calls)) for name, seconds, calls in
                 re.findall(r'^PHASE (\S+) ([0-9.]+) (\d+)$', output.read_text(), re.M)}
        app_seconds = phase['whole_run']['seconds']
        elapsed = float(receipt['card_minutes']) * 60
        assert elapsed > 0 and app_seconds > 0
        host = RUNS / (case + '-t12')
        quick_host = RUNS / ('quick-' + case)
        identity_host = RUNS / ('tree-' + case + '-t12')
        best = min(float((p / 'seconds.txt').read_text()) for p in (host, quick_host, identity_host)
                   if (p / 'exit.txt').read_text().strip() == '0')
        competitors = BUILD / 'host-competitors.json'
        if competitors.is_file():
            for row in json.loads(competitors.read_text()).values():
                candidate = ROOT / row['cases'][case]['run']
                assert compare.load_run(reference)[0].hex() == compare.load_run(candidate)[0].hex()
                assert row['cases'][case]['bit_identical']
                best = min(best, float(row['cases'][case]['seconds']))
        vector = BUILD / 'portable-vector-competitor.json'
        if vector.is_file():
            row = json.loads(vector.read_text())['cases'][case]
            assert compare.load_run(reference)[0].hex() == compare.load_run(ROOT / row['run'])[0].hex()
            assert row['bit_identical']
            best = min(best, float(row['seconds']))
        # Faster pre-existing observations are conservative competitors too;
        # contended correctness timings must not inflate the apparent gain.
        best = min(best, {'large': 21.9, 'core-small': 37.0}[case])
        sequential = BUILD / 'sequential-benchmarks.json'
        if sequential.is_file():
            runs = json.loads(sequential.read_text())
            for label, row in runs.items():
                entry = row['cases'][case]
                assert entry['bit_identical']
                assert compare.load_run(reference)[0].hex() == compare.load_run(ROOT / entry['run'])[0].hex()
                if label != 'stock-196':
                    best = min(best, float(entry['seconds']))
        stock_run = RUNS / ('stock-' + case)
        if not stock_run.is_dir():
            stock_run = RUNS.parent / ('stock-' + case)
        if sequential.is_file():
            stock_run = ROOT / json.loads(sequential.read_text())['stock-196']['cases'][case]['run']
        assert compare.load_run(reference)[0].hex() == compare.load_run(stock_run)[0].hex()
        evidence[case] = dict(binary_sha256=binary_hash, threads=240, bit_identical=True,
                              seconds=max(elapsed, app_seconds), app_seconds=app_seconds,
                              best_x86_12_seconds=best, stock_196_seconds=float((stock_run / 'seconds.txt').read_text()),
                              phase=phase, receipt_sha256=sha(receipt_path), output_sha256=sha(output), batch=number)
    projection = BUILD / 'full-projection.json'
    if projection.is_file():
        evidence['full-117676-projection'] = json.loads(projection.read_text())
    write_json(BUILD / 'card-results.json', evidence)
    print('Imported exact native measurements; run the full acceptance gate to judge 2x.', flush=True)


def stage():
    out = ROOT / 'runs/card/s8-09'
    out.mkdir(parents=True, exist_ok=True)
    number = 1
    while (BUILD / ('card-batch-%d.sh' % number)).exists():
        number += 1
    frozen = BUILD / ('batch-%d' % number)
    frozen.mkdir()
    shutil.copyfile(BUILD / 'card/milkyway_nbody.mic', frozen / 'milkyway_nbody.mic')
    shutil.copyfile(ROOT / 'config/s8-09.env', frozen / 'options.env')
    shutil.copyfile(BUILD / 'manifest.json', frozen / 'manifest.json')
    commands = ['#!/usr/bin/env bash', '# Lead only, inside a granted card window.',
                'set -uo pipefail', 'cd "$(dirname "$0")/../.."']
    # Script lives build/s8-09, so two levels gives the worktree root.
    for case in ('large', 'core-small'):
        label = 'batch-%d-%s-240' % (number, case)
        cmd = ['python', 'tools/card_run', '--benchmark',
               '--threads', '240', '--timeout', '900', '--receipt', 'runs/card/s8-09/' + label + '.json',
               '--file', 'build/s8-09/batch-%d/milkyway_nbody.mic' % number,
               '--file', 'workunits/' + case + '/params.lua']
        hist = 'OCS_data_2025_north_194.hist' if case == 'core-small' else 'input.hist'
        cmd += ['--file', 'workunits/' + case + '/' + hist]
        for runtime in ('libgomp.so.1', 'libstdc++.so.6', 'libgcc_s.so.1'):
            cmd += ['--file', 'dist/card/' + runtime]
        cmd += ['scripts/card-launch.sh', 'OMP_NUM_THREADS=240']
        args = arguments(case, 240)
        args[1], args[3] = 'params.lua', hist
        cmd += args
        commands.append(' '.join(shlex.quote(part) for part in cmd) + ' > runs/card/s8-09/' + label + '.txt 2>&1')
        commands.append('echo "$?" > runs/card/s8-09/' + label + '.exit')
    (BUILD / ('card-batch-%d.sh' % number)).write_bytes(('\n'.join(commands) + '\n').encode())
    print('Staged two frozen jobs: build/s8-09/card-batch-%d.sh' % number, flush=True)


if __name__ == '__main__':
    os.chdir(ROOT)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('manifest', 'stage', 'proof', 'matrix', 'stock', 'quick', 'import-card'))
    parser.add_argument('--batch', type=int, default=2)
    parser.add_argument('--skip-full', action='store_true', help='development only; acceptance still requires full bodies')
    args = parser.parse_args()
    BUILD.mkdir(parents=True, exist_ok=True)
    RUNS.mkdir(parents=True, exist_ok=True)
    if args.action == 'import-card':
        import_card(args.batch)
    elif args.action == 'proof':
        proof(not args.skip_full)
    else:
        globals()[args.action]()
