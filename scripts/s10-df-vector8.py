"""S10-09 evidence driver. All host runs use four OpenMP threads."""
import datetime
import hashlib
from importlib import import_module
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import time
import compare
old = import_module('s10-df-special')
ROOT = Path(__file__).resolve().parents[1]
B = ROOT / 'build/s10/df-vector8'
RUNS = ROOT / 'runs/s10-df-vector8'
ARGS = old.ARGS
VARIANTS = ['release', 'vector8', 'guard', 'scalar', 'scalar-guard']
sha, save, rel = old.sha, old.save, old.rel

def prepare(variant):
    tree = B / (variant + '-tree')
    u = ROOT / 'third_party/milkywayathome_client_196'
    for name in ['nbody/src/nbody_mixeddwarf.c', 'nbody/include/nbody_df_special.h', 'nbody/include/nbody_gen_profile.h']:
        dest = tree / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(u / name, dest)
    source = (tree / 'nbody/src/nbody_mixeddwarf.c').read_text()
    # Test-only instrumentation, never in the Performance patch or timing app.
    header = (ROOT / 'src/nbody_df_vector8.h').read_text()
    hook = '    for (size_t i=0;i<lanes;++i) output[i]=result[i];'
    assert header.count(hook) == 1
    (tree / 'nbody/include/nbody_df_vector8.h').write_bytes((header.replace(hook, hook +
        '\n#ifdef S10_NODE_CAPTURE\n    s10_nodes_capture(x,lanes,a,b,energy,dark,output);\n#endif')).encode())
    for a, b in [('#include "nbody_king_model.h"', '#include "nbody_king_model.h"\n#include "s10_df_vector8_capture.h"\n#define S10_NODE_CAPTURE 1'),
                 ('        unsigned int i = 0;', '        double s8_start = s8_capture_start();\n        s10_rng_open(); s10_nodes_open();\n        unsigned int i = 0;'),
                 ('            GP_BODY_END();', '            s10_rng_body(prng);\n            GP_BODY_END();'),
                 ('        /* pushing the bodies */', '        s10_rng_close(); s10_nodes_close();\n        fprintf(stderr,"DF8_GUARD_TRIGGERS=%u\\n",s10_guard_triggers);\n        s8_capture_end(s8_start,nbody,x,y,z,vx,vy,vz,masses);\n        /* pushing the bodies */'),
                 ('        *rng=saved;', '        ++s10_guard_triggers;\n        *rng=saved;')]:
        assert source.count(a) == 1, a
        source = source.replace(a, b)
    source += '''
/* Capture the first real quadrature batches, under the same four-thread run.
 * All records are independent; file order is the team's observed arrival order. */
static void s10_nodes_capture(const real* x,size_t lanes,const Dwarf* a,const Dwarf* b,real e,mwbool dark,const real* fast)
{
    if (!s10_node_file) return;
    #pragma omp critical(s10_node_capture)
    {
        if (s10_node_records[!!dark]<32) {
            uint64_t n=lanes, component=dark;
            real xs[8]={0}, ys[8]={0}, exact[8]={0};
            for(size_t i=0;i<lanes;++i) {xs[i]=x[i];ys[i]=fast[i];exact[i]=fun(x[i],a,b,e,dark);}
            if(fwrite(&n,8,1,s10_node_file)!=1 || fwrite(a,sizeof(*a),1,s10_node_file)!=1 ||
               fwrite(b,sizeof(*b),1,s10_node_file)!=1 || fwrite(&e,8,1,s10_node_file)!=1 ||
               fwrite(&component,8,1,s10_node_file)!=1 || fwrite(xs,64,1,s10_node_file)!=1 ||
               fwrite(ys,64,1,s10_node_file)!=1 || fwrite(exact,64,1,s10_node_file)!=1) abort();
            ++s10_node_records[!!dark];
        }
    }
}
'''
    (B / (variant + '-capture.c')).write_bytes(source.encode())
    shutil.copyfile(u / 'nbody/include/nbody_gen_profile.h', B / 'nbody_gen_profile.h')

def calibrate(variant='vector8'):
    suffix = '-scalar' if variant == 'scalar' else ''
    p = json.loads((B / ('kernel'+suffix+'.json')).read_text())
    # max relative to |fast|+|exact|. Comparison differences combine two
    # evaluations; an additional 1000x factor covers that and unseen samples.
    # This is an empirical guard, not a certified interval or correctness proof.
    p = dict(comparisons=p['comparisons'], max_normalized_difference=p['max_normalized_difference'],
             safety_factor=1000, margin=max(1e-8, 1000 * p['max_normalized_difference']),
             policy='|a-b| <= margin*(|a|+|b|); nonfinite decisions replay; empirical only')
    save(B / ('calibration'+suffix+'.json'), p)
    print(json.dumps(p), flush=True)

def run(variant, case):
    if case == '117676':
        raise RuntimeError('Owner 2026-11-17 19:45Z canceled all further full host captures; short cases only')
    assert case in ['core-small','real-steps']
    label = case + '-' + variant
    out = RUNS / label
    out.mkdir(parents=True, exist_ok=True)
    exe = B / ('x86-' + variant) / 'capture.exe'
    cmd = [str(exe), '-f', str(ROOT / ('workunits/' + case + '/params.lua')),
           '-h', str(ROOT / 'workunits/core-small/OCS_data_2025_north_194.hist'),
           '-z', str(out / 'histogram.txt'), '-c', str(out / 'checkpoint'),
           '--seed', '65477096', '--nthreads', '4', '--print-histogram',
           '--ignore-checkpoint', '--checkpoint-interval=-1', '-np', '14', '-p'] + ARGS
    env = dict(os.environ, OMP_NUM_THREADS='4', OMP_DYNAMIC='FALSE',
               S8_INITIAL_BODIES=str(out / 'initial-bodies.bin'), S10_RNG_TRACE=str(out / 'rng.bin'))
    if case == 'core-small' and variant in ['vector8','scalar']: env['S10_NODE_TRACE'] = str(out / 'node-inputs.bin')
    save(out / 'command.json', cmd)
    t = time.monotonic()
    with (out / 'stdout.txt').open('w') as stdout, (out / 'stderr.txt').open('w') as stderr:
        result = subprocess.run(cmd, cwd=out, env=env, stdout=stdout, stderr=stderr)
    seconds = time.monotonic() - t
    (out / 'exit.txt').write_text(str(result.returncode) + '\n')
    assert result.returncode == 0, (label, result.returncode)
    text = (out / 'stderr.txt').read_text()
    row = dict(binary=rel(exe), binary_sha256=sha(exe), threads=4, run=rel(out),
               generation_seconds=float(re.search(r'S8_GENERATION_SECONDS=([\d.]+)', text)[1]),
               whole_seconds=seconds, rng_record_bytes=int(re.search(r'S10_RNG_RECORD_BYTES=(\d+)', text)[1]),
               guard_triggers=int(re.search(r'DF8_GUARD_TRIGGERS=(\d+)', text)[1]))
    row['likelihood_hex'] = compare.load_run(out)[0].hex()
    save(B / (label + '.json'), row)
    print(json.dumps(row, indent=2), flush=True)

def differences():
    result = {}
    for case in ['core-small', 'real-steps']:
        ref = json.loads((B / (case + '-release.json')).read_text())
        ar = ROOT / ref['run']
        result[case] = {}
        for variant in VARIANTS[1:]:
            fast = json.loads((B / (case + '-' + variant + '.json')).read_text())
            br = ROOT / fast['run']
            n, first = old.file_differences(ar / 'initial-bodies.bin', br / 'initial-bodies.bin', 56)
            assert ref['rng_record_bytes'] == fast['rng_record_bytes']
            nr, firstr = old.file_differences(ar / 'rng.bin', br / 'rng.bin', ref['rng_record_bytes'])
            row = dict(reference=rel(ar), experiment=rel(br), different_bodies=n, first_different_body=first,
                       different_rng_states=nr, first_rng_divergence_body=firstr, rng_record_bytes=ref['rng_record_bytes'],
                       indexing='zero based; RNG state at end of body, before CM correction',
                       guard_triggers=fast['guard_triggers'])
            x, y = (compare.load_run(d)[0] for d in [ar, br])
            row.update(exact_likelihood_hex=x.hex(), experiment_likelihood_hex=y.hex(), likelihood_difference=y-x)
            result[case][variant] = row
    save(B / 'differences.json', result)
    print(json.dumps(result, indent=2), flush=True)

def stage(window_only=None):
    prediction = ('Uncalibrated hypotheses, recorded before card execution: release setup core-small 45-55 s, '
                  'real-steps 225-260 s; vector8 core-small 15-50 s, real-steps 80-250 s. '
                  'Guard adds exact replay cost proportional to the measured host trigger fraction; '
                  'allow up to 2x vector8 time. No native numerical equality or speed gain is assumed. '
                  'Scalar crlibm log/atan with vector remainder: core-small 25-65 s, real-steps 120-300 s; '
                  'its guard has the same replay-cost caveat. The two log/atan modes are owner-requested comparisons. '
                  'Twin audit support status is in twin-effort.json; it supplies no calibrated forecast.')
    lines = ['#!/usr/bin/env bash', '# Lead only, inside an authorized card window.',
             'set -euo pipefail', 'cd "$(dirname "$0")/../../.."',
             'mkdir -p runs/card/s10-df-vector8', '# Prediction: ' + prediction]
    scalar_lines=list(lines)
    for case in ['core-small', 'real-steps']:
        for variant in VARIANTS:
            exe = B / ('card-' + variant) / 'milkyway_nbody.mic'
            label = variant + '-' + case + '-240'
            cmd = ['python', 'tools/card_run', '--benchmark', '--threads', '240',
                   '--transfer', 'tcp-large', '--transport-timeout', '300', '--stage-timeout', '600',
                   '--timeout', '1800', '--receipt', 'runs/card/s10-df-vector8/' + label + '.json',
                   '--file', rel(exe), '--file', 'workunits/' + case + '/params.lua',
                   '--file', 'workunits/core-small/OCS_data_2025_north_194.hist']
            for runtime in sorted((B / 'runtimes').iterdir()): cmd += ['--file', rel(runtime)]
            cmd += ['scripts/card-launch-env.sh', 'OMP_NUM_THREADS=240', './milkyway_nbody.mic',
                    '-f', 'params.lua', '-h', 'OCS_data_2025_north_194.hist', '--seed', '65477096',
                    '--nthreads', '240', '--print-histogram', '--ignore-checkpoint',
                    '--checkpoint-interval=-1', '-np', '14', '-p'] + ARGS
            job_lines=['# SHA256 ' + sha(exe),
                       ' '.join(shlex.quote(x) for x in cmd) + ' > runs/card/s10-df-vector8/' + label + '.txt 2>&1']
            lines += job_lines
            if variant in ['scalar','scalar-guard']:scalar_lines += job_lines
    lines += ['python scripts/s10-df-vector8.py card_report']
    window_bytes=('\n'.join(lines) + '\n').encode()
    if not (B/'card-window.sh').exists() or (B/'card-window.sh').read_bytes()!=window_bytes:
        (B/'card-window.sh').write_bytes(window_bytes)
    scalar_lines += ['# Run after the already-staged reference/all-vector window.',
                     'python scripts/s10-df-vector8.py card_report']
    scalar_bytes=('\n'.join(scalar_lines)+'\n').encode()
    if not (B/'card-window-scalar.sh').exists() or (B/'card-window-scalar.sh').read_bytes()!=scalar_bytes:
        (B/'card-window-scalar.sh').write_bytes(scalar_bytes)
    prediction_file = B / 'prediction-both.json'
    if prediction_file.exists():
        recorded = json.loads(prediction_file.read_text())
        assert recorded['prediction'] == prediction, 'Do not silently revise a frozen prediction'
    else:
        recorded = dict(prediction=prediction,
                        prediction_recorded_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
        save(prediction_file, recorded)
    if window_only:
        return
    paths = [ROOT / p for p in ['mk/Makefile', 'config/release.env', 'patches/zzzzzzz-nbody-df-vector8.patch',
             'src/nbody_df_vector8.h', 'scripts/build-s10-df-vector8.sh', 'scripts/s10-df-vector8.py',
             'scripts/test-s10-df-vector8.sh', 'scripts/s10-df-vector8-compiler.sh',
             'scripts/twin-s10-df-vector8.py', 'probes/s10_df_vector8_twin.c',
             'tests/s10_df_vector8_capture.h',
             'tests/s10-df-vector8.mk', 'tests/s10_df_vector8_kernel.c', 'tests/test_s10_df_vector8.py',
             'probes/s10_df_vector8_repro.c', 'docs/research/s10-df-vector8.md']]
    paths += [p for p in B.rglob('*') if p.is_file() and p.name != 'handoff.json' and p.suffix in
              ['.mic', '.exe', '.json', '.txt', '.sh', '.c', '.h'] and not p.name.endswith('-started.json')]
    paths += list((B / 'runtimes').iterdir())
    paths += [B / 'twin-node-inputs.bin', B / 'twin-node-inputs-scalar.bin']
    paths += [B / ('card-' + v) / '.build-options' for v in VARIANTS]
    paths += [p for p in RUNS.rglob('*') if p.is_file()]
    # Do not hash transient acceptance output that changes when rechecked.
    paths = [p for p in paths if p.name != 'acceptance-after.txt']
    save(B / 'handoff.json', dict(prediction=prediction,
         prediction_recorded_utc=recorded['prediction_recorded_utc'],
         files={rel(p): sha(p) for p in paths}))

def card_report():
    folder = ROOT / 'runs/card/s10-df-vector8'
    rows = {}
    for case in ['core-small', 'real-steps']:
        rows[case] = {}
        for variant in VARIANTS:
            label = variant + '-' + case + '-240'
            likelihood = compare.load_run(folder / (label + '.txt'))[0]
            receipt = json.loads((folder / (label + '.json')).read_text())
            assert receipt['exit_code'] == 0
            rows[case][variant] = dict(likelihood=likelihood, likelihood_hex=likelihood.hex(),
                                      card_seconds=60*receipt['card_minutes'])
        for variant in VARIANTS[1:]:
            rows[case][variant]['likelihood_difference'] = (rows[case][variant]['likelihood'] -
                                                          rows[case]['release']['likelihood'])
    save(folder / 'summary.json', rows)
    print(json.dumps(rows, indent=2))

if __name__ == '__main__':
    os.chdir(ROOT); B.mkdir(parents=True, exist_ok=True)
    globals()[sys.argv[1]](*sys.argv[2:])
