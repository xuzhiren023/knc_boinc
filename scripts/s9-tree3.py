"""S9-04 exact host proof, read-only balance model, and lead-only card jobs."""
import hashlib
import heapq
import json
from pathlib import Path
import re
import shlex
import shutil
import statistics
import subprocess
import sys

import compare
import s8_integration as harness

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'build/s9'
RUNS = ROOT / 'runs/s9-tree3'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def proof():
    harness.RUNS = RUNS
    binary = BUILD / 'x86-tree3/milkyway_nbody.exe'
    evidence = dict(binary_sha256=digest(binary), runs={})
    log = []
    for case in ('small', 'medium', 'large'):
        source = ROOT.parent / 'S7-01/runs/force-chunk' / (case + '-chunk196-default-t12')
        reference = RUNS / (case + '-reference')
        reference.mkdir(parents=True, exist_ok=True)
        hashes = {}
        for name in ('stdout.txt', 'stderr.txt', 'histogram.txt', 'exit.txt'):
            shutil.copyfile(source / name, reference / name)
            hashes[str(source / name)] = digest(source / name)
        write_json(reference / 'provenance.json', hashes)
        for threads in (1, 12):
            label = '%s-t%d' % (case, threads)
            run = harness.run(binary, case, threads, label)
            command = [sys.executable, str(ROOT / 'scripts/compare.py'), str(reference), str(run)]
            result = subprocess.check_output(command, text=True)
            assert compare.load_run(reference) == compare.load_run(run), 'exact science mismatch: ' + label
            text = compare.captured_output(run)
            checks = re.findall(r'^TREE_IDENTITY step=(\d+).* PASS$', text, re.M)
            calls = int(re.search(r'^PHASE nbMakeTree \S+ (\d+)$', text, re.M)[1])
            assert list(map(int, checks)) == [0] + list(range(calls - 1)), label
            evidence['runs'][label] = dict(run=run.relative_to(ROOT).as_posix(),
                reference=reference.relative_to(ROOT).as_posix(), identity_builds=calls,
                likelihood_hex=compare.load_run(run)[0].hex(), compare=result)
            entry = '%s: %d/%d every-build identity PASS\n%sExact likelihood: %s\n' % (
                label, len(checks), calls, result, compare.load_run(run)[0].hex())
            print(entry, flush=True)
            log.append(entry)
    write_json(BUILD / 'tree3-proof.json', evidence)
    (BUILD / 'tree3-proof.txt').write_text('\n'.join(log))
    model()


def critical(counts):
    loads = [0] * 240
    heapq.heapify(loads)
    for count in sorted(counts, reverse=True):
        heapq.heapreplace(loads, loads[0] + count)
    return max(loads)


def model():
    cases = {}
    for case in ('small', 'medium', 'large'):
        text = compare.captured_output(RUNS / (case + '-t12'))
        samples = {2: [], 3: []}
        pattern = r'^TREE_MODEL step=(\d+) variant=(\d) threads=240 top=(\d+) visits=(\d+) counts=(.*)$'
        cells = [int(value) for value in re.findall(r'^TREE_IDENTITY .* cells=(\d+) ', text, re.M)]
        for step, variant, top, visits, values in re.findall(pattern, text, re.M):
            counts = [int(value) for value in values.split(',') if value]
            samples[int(variant)].append(dict(step=int(step), top=int(top), visits=int(visits),
                jobs=len(counts), bodies=sum(counts), max=max(counts, default=0),
                critical=critical(counts)))
        assert len(samples[2]) == len(samples[3]) == len(cells)
        summary = {}
        for variant, rows in samples.items():
            summary[str(variant)] = {key: statistics.mean(row[key] for row in rows)
                for key in ('top', 'visits', 'jobs', 'bodies', 'max', 'critical')}
            summary[str(variant)]['worst_max'] = max(row['max'] for row in rows)
        cases[case] = dict(builds=len(cells), cells=statistics.mean(cells), variants=summary,
                           samples=samples)
    large = cases['large']
    old, new = [large['variants'][str(v)] for v in (2, 3)]
    # Count-calibrated estimate, not host wall-clock extrapolation. Old parallel
    # phases set the cost per critical-path body; serial cell work is converted
    # using the measured serial phase/cell. The 0.02 s/phase term allows for
    # dispatch and barriers across 111 tree builds (an explicit assumption).
    overhead = 0.02
    top_fraction = new['top'] / large['cells']
    ratio = new['critical'] / old['critical']
    seconds = dict(expandBox=0.13)
    seconds['insertion'] = 3.12 * ratio + overhead
    for name, old_time, serial_time in [('hackCofM', 2.24, 2.37), ('hackQuad', 2.48, 2.69)]:
        seconds[name] = old_time * ratio + serial_time * top_fraction + overhead
    seconds['threadTree'] = 1.82 * (top_fraction + (1 - top_fraction) * new['critical'] / 20000) + overhead
    # Fixed D3 partition has 3 key-level visits/body, two serial passes/body
    # and 73 possible top cells. Adaptive has two serial octant passes and
    # scatter+copy per visit. Charge 4/2=2 old serial-pass equivalents per
    # adaptive body visit, plus cell creation, to expose partition risk.
    seconds['partition'] = 0.14 * (2 * new['visits'] + new['top']) / (2 * 20000 + old['top'])
    value = dict(cases=cases, seconds=seconds, total_seconds=sum(seconds.values()), k=4,
        model_table_used=False, old_critical_to_new_ratio=ratio,
        formula='Parallel phases: old_pool_seconds * LPT240(new)/LPT240(old) + serial_seconds * new_top/total_cells + 0.02. Insertion omits top term (charged to partition). Thread: 1.82*(top/cells + (1-top/cells)*LPT240(new)/20000)+0.02. Partition: 0.14*(2*new_body_visits+new_top)/(40000+old_top). Expand: 0.13.',
        limitations='Body counts proxy work; ignores varying subtree depths, x87/cache effects and atomic-slab contention. Partition calibration assumes serial old passes dominate its 0.14 s. No native measurements. Serial boundary repair and synchronization may increase threading cost.')
    write_json(BUILD / 'tree3-model.json', value)
    lines = ['S9-04 card prediction (large, 20,000 bodies, 111 builds, 240 threads)',
             'k=4; LPT240 uses descending body counts and least-loaded worker.', value['formula']]
    for case, row in cases.items():
        lines.append('%s: %s' % (case, json.dumps({k: v for k, v in row.items() if k != 'samples'}, sort_keys=True)))
    lines += ['%s: %.3f s' % item for item in seconds.items()]
    lines += ['nbMakeTree subphase sum: %.3f s' % sum(seconds.values()), value['limitations']]
    (BUILD / 'tree3-prediction.txt').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines), flush=True)


def stage():
    out = ROOT / 'runs/card/s9-tree3'
    out.mkdir(parents=True, exist_ok=True)
    lines = ['#!/usr/bin/env bash', '# Lead only, inside an authorized card window.',
             'set -euo pipefail', 'cd "$(dirname "$0")/../.."', 'mkdir -p runs/card/s9-tree3']
    for case in ('large', 'core-small'):
        hist = 'OCS_data_2025_north_194.hist' if case == 'core-small' else 'input.hist'
        args = harness.arguments(case, 240)
        args[1], args[3] = 'params.lua', hist
        command = ['python', 'tools/card_run', '--benchmark', '--threads', '240', '--timeout', '900',
            '--receipt', 'runs/card/s9-tree3/' + case + '.json',
            '--file', 'build/s9/card-tree3/milkyway_nbody.mic',
            '--file', 'workunits/' + case + '/params.lua', '--file', 'workunits/' + case + '/' + hist]
        for runtime in ('libgomp.so.1', 'libstdc++.so.6', 'libgcc_s.so.1'):
            command += ['--file', 'build/s9/runtimes/' + runtime]
        command += ['scripts/card-launch-env.sh', 'OMP_NUM_THREADS=240', './milkyway_nbody.mic'] + args
        lines.append(' '.join(shlex.quote(part) for part in command) + ' > runs/card/s9-tree3/' + case + '.txt 2>&1')
    (BUILD / 'tree3-window.sh').write_bytes(('\n'.join(lines) + '\n').encode())
    write_json(BUILD / 'tree3-card-manifest.json', dict(binary_sha256=digest(BUILD / 'card-tree3/milkyway_nbody.mic'),
        files={str(p.relative_to(ROOT)): digest(p) for p in sorted((ROOT / 'patches').glob('*.patch'))}))


if __name__ == '__main__':
    {'proof': proof, 'model': model, 'stage': stage}[sys.argv[1]]()
