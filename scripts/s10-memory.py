"""S10-07 exact force proof and lead-only card handoff."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import compare
import s8_integration as harness
ROOT=Path(__file__).resolve().parents[1]
B=ROOT/'build/s10-memory'; RUNS=ROOT/'runs/s10-memory'
VARIANTS=('base','order','huge','both')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_bytes((json.dumps(x,indent=2)+'\n').encode())
def relative(p): return p.relative_to(ROOT).as_posix()
def cases(): return ('small','medium','large','real-steps' if (ROOT/'workunits/real-steps').exists() else 'core-small')
def arguments(case,threads):
    if case!='real-steps':return harness.arguments(case,threads)
    args=harness.arguments('core-small',threads)
    args=[s.replace('workunits/core-small/','workunits/real-steps/') for s in args]
    return args

def proof():
    harness.RUNS=RUNS; arguments_original=harness.arguments
    # Let the existing harness resolve real-steps identically to core-small.
    if 'real-steps' in cases():
        def real_args(c,t):
            if c=='real-steps':return [s.replace('workunits/core-small/','workunits/real-steps/') for s in arguments_original('core-small',t)]
            return arguments_original(c,t)
        harness.arguments=real_args
    prior=json.loads((B/'proof.json').read_text()) if (B/'proof.json').exists() else {'runs':{}}
    result={'runs':{}}
    for case in cases():
        ref=RUNS/('base-'+case)
        for variant in VARIANTS:
            binary=B/('x86-'+variant+'/milkyway_nbody.exe')
            label=variant+'-'+case; run=RUNS/label
            old=prior['runs'].get(label)
            reuse=old and old['binary_sha256']==sha(binary) and (run/'exit.txt').read_text().strip()=='0' and sha(run/'forces.bin')==old['force_sha256']
            if not reuse:
                run=harness.run(binary,case,1 if case=='small' else 4,label,{'NBODY_WALK_FORCE_DUMP':str(run/'forces.bin'),
                    'OMP_WAIT_POLICY':'PASSIVE','GOMP_SPINCOUNT':'0'})
            output=subprocess.check_output([sys.executable,ROOT/'scripts/compare.py',ref,run],text=True)
            assert compare.load_run(ref)==compare.load_run(run), label
            assert (run/'forces.bin').read_bytes()==(ref/'forces.bin').read_bytes(),label+' force mismatch'
            text=compare.captured_output(run)
            maps=int(re.search(r'^PHASE nbMapForceBody \S+ (\d+)$',text,re.M)[1])
            nbody=(run/'forces.bin').stat().st_size//(24*maps)
            assert nbody == dict(small=64,medium=1024,large=20000).get(case,nbody) and nbody>0, (case,nbody)
            assert (run/'forces.bin').stat().st_size==nbody*24*maps
            run_args=json.loads((run/'command.json').read_text())
            result['runs'][label]=dict(run=relative(run),reference=relative(ref),binary_sha256=sha(binary),
                force_sha256=sha(run/'forces.bin'),maps=maps,nbody=nbody,threads=int(run_args[run_args.index('--nthreads')+1]),compare=output)
            save(B/'proof.json',result)
            print('%s: %d maps x %d forces, xyz bytes identical; %s'%(label,maps,nbody,output.strip()),flush=True)
        if case!='real-steps':
            # Independent prior science reference, not solely our option-off build.
            oldref=harness.copy_reference(case)
            assert compare.load_run(oldref)==compare.load_run(ref),case+' prior science reference'
            if case in ('small','medium','large'):
                forces=ROOT.parent/'S8-08/build/s8'/('walk-reference-x86-%s-12-forces.bin'%case)
                assert forces.read_bytes()==(ref/'forces.bin').read_bytes(),case+' prior force reference'
            print('PASS independent prior reference '+case,flush=True)
    save(B/'proof.json',result)

def stage():
    twin=json.loads((B/'twin/evidence.json').read_text())
    lines=['#!/usr/bin/env bash','# Lead only, within an authorized card window. Predictions frozen before card execution.',
        'set -euo pipefail','cd "$(dirname "$0")/../.."','mkdir -p runs/card/s10-memory']
    jobs=[]
    predictions={'base':'Repeat control. No new measured baseline.',
        'order':'Core twin: no clear difference within conservative band; spatial sample is slower. Eight-tile overlook: no clear difference. Host counters suggest locality opportunity. Screen 0-20% lower walk or a loss from imbalance/permutation; large force 0-5% lower before overhead.',
        'huge':'Hypothesis: 0-10% lower walk only if explicit backing succeeds; otherwise no gain. Large force 0-2.5% lower before overhead.',
        'both':'No twin-confirmed order gain. Hypothesis: 0-25% lower walk, large force 0-6.25% lower before overhead, or a loss; contingent on actual THP backing and balance.'}
    for variant in VARIANTS+('pages',):
        use_cases=('large',) if variant=='pages' else ('large',cases()[-1])
        for case in use_cases:
            folder='card-'+variant
            binary=B/(folder+'/milkyway_nbody.mic')
            hist='OCS_data_2025_north_194.hist' if case in ('core-small','real-steps') else 'input.hist'
            args=arguments(case,240);args[1]='params.lua';args[3]=hist
            cmd=['python','tools/card_run','--benchmark','--threads','240','--timeout','900',
                '--receipt','runs/card/s10-memory/'+variant+'-'+case+'.json',
                '--collect','claude-stderr.txt','--file','build/s10-memory/walk-affinity.mic','--file',relative(binary),
                '--file','workunits/'+case+'/params.lua','--file','workunits/'+case+'/'+hist]
            for lib in sorted((B/'runtimes').iterdir()):cmd+=['--file',relative(lib)]
            cmd+=['scripts/s10-memory-launch.sh','./milkyway_nbody.mic']+args
            prediction=predictions.get(variant,'Diagnostic only; exclude from timing ranking. Report live tree/body alignment and AnonHugePages.')
            lines.append('# Prediction '+variant+'/'+case+': '+prediction)
            lines.append(' '.join(shlex.quote(s) for s in cmd)+' > runs/card/s10-memory/'+variant+'-'+case+'.txt 2>&1')
            jobs.append(dict(variant=variant,case=case,binary=relative(binary),binary_sha256=sha(binary),prediction=prediction))
    (B/'window.sh').write_bytes(('\n'.join(lines)+'\n').encode())
    prediction_lines=['Recorded before card execution; screening hypotheses, no measured gains.']
    prediction_lines.extend(r['variant']+'/'+r['case']+': '+r['prediction'] for r in jobs)
    (B/'predictions.txt').write_bytes((chr(10).join(prediction_lines)+chr(10)).encode())
    files=[B/'predictions.txt',ROOT/'patches/README.md', ROOT/'config/release.env', ROOT/'mk/Makefile', B/'window.sh', B/'model.json', B/'model.txt', B/'real-steps-source.json', B/'proof.json', B/'proof.txt', B/'twin/evidence.json',ROOT/'docs/research/s10-walk-memory.md']
    files+=sorted((ROOT/'patches').glob('*.patch'))+sorted((ROOT/'src').glob('nbody_walk*.h'))
    files+=sorted((ROOT/'scripts').glob('*s10-memory*'))+[ROOT/'scripts/twin_s10_memory_common.py',ROOT/'tests/test_s10_memory.py']
    files += [B/('capture-base'+suffix) for suffix in ('.bin','.json','-provenance.json')]
    files += [B/'layout-card.s',B/'layout-x86.s',B/'model-capture.bin',B/'model-capture.json',B/'model-layout.s']
    for archive in ('initial-two-call-attempt','full-background-one-call'):
        folder=B/'twin'/archive
        files += list(folder.rglob('result.json')) + list(folder.glob('*-kernel.json'))
    files += sorted((B/'twin').glob('*/result.json')) + sorted((B/'twin').glob('*-kernel.json'))
    for variant in VARIANTS:
        folder=B/('x86-'+variant)
        files += [folder/'milkyway_nbody.exe',folder/'.build-options']
    files+=list((B/'runtimes').iterdir())+[B/'walk-affinity.mic',ROOT/'probes/s10_memory_affinity.c']
    for row in jobs:
        binary=ROOT/row['binary'];files += [binary,binary.parent/'.build-options',binary.parent/'knc-lint.txt']
        files+=list((ROOT/'workunits'/row['case']).glob('*'))
    release=[]
    for v in VARIANTS:
        p=B/('card-release-'+v+'/milkyway_nbody.mic')
        release.append(dict(variant=v,binary=relative(p),binary_sha256=sha(p)))
        files += [p,p.parent/'.build-options',p.parent/'knc-lint.txt']
    save(B/'card-manifest.json',dict(twin_scope='Unvalidated cold walk diagnostic; four contexts/core, eight detailed ring tiles, no extra synthetic cores.',release_binaries=release,recorded_at=datetime.now(timezone.utc).isoformat(),jobs=jobs,twin=twin,
        files={relative(p):sha(p) for p in files if p.is_file()}))
    print('Staged %d lead-only jobs; no card access.'%len(jobs))
if __name__=='__main__': {'proof':proof,'stage':stage}[sys.argv[1]]()
