"""S9-06 exact host proof, read-only balance model, and lead-only card jobs."""
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
RUNS = ROOT / 'runs/s9-tree4'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def proof():
    harness.RUNS = RUNS
    binary = BUILD / 'x86-tree4/milkyway_nbody.exe'
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
    write_json(BUILD / 'tree4-proof.json', evidence)
    (BUILD / 'tree4-proof.txt').write_text('\n'.join(log))
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
    new = large['variants']['3']  # Variant 4 has exactly the same frontier.
    # Calibrate to the ticket's actual variant-3 partition measurement, not
    # S9-04's earlier estimate. Body work is parallel; upper-cell creation and
    # level dispatch are still serial. Explicit assumptions, not a fitted table.
    serial_fraction = 0.05
    work_multiplier = 2.0  # prefix metadata, extra barriers and scratch traffic
    effective_workers = 24  # 10% of 240 hardware threads, conservative bandwidth
    dispatch_seconds = 0.15  # all levels across all 111 builds
    baseline = 5.93
    partition = baseline * (serial_fraction + (1 - serial_fraction) *
                            work_multiplier / effective_workers) + dispatch_seconds
    value = dict(cases=cases, baseline_partition_seconds=baseline,
        partition_seconds=partition, serial_fraction=serial_fraction,
        parallel_work_multiplier=work_multiplier, effective_workers=effective_workers,
        dispatch_seconds=dispatch_seconds, model_table_used=False,
        formula='5.93*(0.05 + 0.95*2/24) + 0.15',
        limitations='Assumes 5% serial upper-cell/metadata work, 2x parallel work per body-level visit, 24 effective workers and 0.15 s total dispatch overhead. No native measurements; bandwidth, barrier latency, long unary paths and serial prefixes can dominate.')
    write_json(BUILD / 'tree4-model.json', value)
    lines = ['S9-06 card prediction, before any card run: large, 20,000 bodies, 111 builds, 240 threads.',
             'Variant 4 retains variant 3 frontier counts: mean top=%.2f, visits=%.2f, jobs=%.2f.' %
             (new['top'], new['visits'], new['jobs']),
             'Partition: %s = %.3f s (baseline 5.930 s).' % (value['formula'], partition),
             'Holding other subphases fixed: nbMakeTree ~%.3f s, whole run ~%.3f s.' %
             (7.08 - baseline + partition, 20.95 - baseline + partition),
             'Sensitivity, effective workers 12/48: %.3f/%.3f s partition.' %
             tuple(baseline*(serial_fraction+(1-serial_fraction)*work_multiplier/w)+dispatch_seconds for w in (12,48)),
             value['limitations']]
    (BUILD / 'tree4-prediction.txt').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines), flush=True)


def stage():
    out = ROOT / 'runs/card/s9-tree4'
    out.mkdir(parents=True, exist_ok=True)
    lines = ['#!/usr/bin/env bash', '# Lead only, inside an authorized card window.',
             'set -euo pipefail', 'cd "$(dirname "$0")/../.."', 'mkdir -p runs/card/s9-tree4']
    for case in ('large', 'core-small'):
        hist = 'OCS_data_2025_north_194.hist' if case == 'core-small' else 'input.hist'
        args = harness.arguments(case, 240)
        args[1], args[3] = 'params.lua', hist
        command = ['python', 'tools/card_run', '--benchmark', '--threads', '240', '--timeout', '900',
            '--receipt', 'runs/card/s9-tree4/' + case + '.json',
            '--file', 'build/s9/card-tree4/milkyway_nbody.mic',
            '--file', 'workunits/' + case + '/params.lua', '--file', 'workunits/' + case + '/' + hist]
        for runtime in ('libgomp.so.1', 'libstdc++.so.6', 'libgcc_s.so.1'):
            command += ['--file', 'build/s9/runtimes/' + runtime]
        command += ['scripts/card-launch-env.sh', 'OMP_NUM_THREADS=240', './milkyway_nbody.mic'] + args
        lines.append(' '.join(shlex.quote(part) for part in command) + ' > runs/card/s9-tree4/' + case + '.txt 2>&1')
    (BUILD / 'tree4-window.sh').write_bytes(('\n'.join(lines) + '\n').encode())
    write_json(BUILD / 'tree4-card-manifest.json', dict(binary_sha256=digest(BUILD / 'card-tree4/milkyway_nbody.mic'),
        files={str(p.relative_to(ROOT)): digest(p) for p in sorted((ROOT / 'patches').glob('*.patch')) + sorted((BUILD / 'runtimes').iterdir()) + [BUILD / 'card-tree4/.build-options', BUILD / 'tree4-window.sh']}))


if __name__ == '__main__':
    {'proof': proof, 'model': model, 'stage': stage}[sys.argv[1]]()
