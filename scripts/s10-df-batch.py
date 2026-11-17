"""S10-10 retained evidence; host measurements are limited to four threads."""
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
old=import_module('s10-df-special')
ROOT=Path(__file__).resolve().parents[1]
B=ROOT/'build/s10/df-batch'
RUNS=ROOT/'runs/s10-df-batch'
sha,save,rel=old.sha,old.save,old.rel

def write_changed(path,data):
    if not path.exists() or path.read_bytes()!=data:path.write_bytes(data)

def prepare(variant):
    shared=Path('C:/Users/xuzhi/Documents/gcc_knc/.work/_shared')
    libraries={name:sha(shared/path) for name,path in [
        ('installed_card','gcc-knc-16.2.0/lib/gcc/k1om-mpss-linux/16.2.0/libknc_vmath.a'),
        ('snapshot_card','S10-02/knc/libknc_vmath.a'),('snapshot_host','S10-02/host/libknc_vmath.a')]}
    assert libraries['installed_card']==libraries['snapshot_card']=='fc732e6f48b7a4bae49eeb32fe9fd78f730e10597b83cfe0495aca150fc4f786'
    save(B/'library-provenance.json',libraries)
    tree=B/(variant+'-tree');u=ROOT/'third_party/milkywayathome_client_196'
    for name in ['nbody/src/nbody_mixeddwarf.c','nbody/include/nbody_df_special.h','nbody/include/nbody_gen_profile.h']:
        dest=tree/name;dest.parent.mkdir(parents=True,exist_ok=True);write_changed(dest,(u/name).read_bytes())
    source=(tree/'nbody/src/nbody_mixeddwarf.c').read_text()
    # Instrumentation stays outside the Performance patch and timing binary.
    for a,b in [('#include "nbody_king_model.h"','#include "nbody_king_model.h"\n#include "s10_df_batch_capture.h"'),
        ('        unsigned int i = 0;','        double s8_start=s8_capture_start();s10_rng_open();\n        unsigned int i = 0;'),
        ('            GP_BODY_END();','            s10_rng_body(prng);\n            GP_BODY_END();'),
        ('        /* pushing the bodies */','        s10_rng_close();dfb_counts_report();\n        s8_capture_end(s8_start,nbody,x,y,z,vx,vy,vz,masses);\n        /* pushing the bodies */'),
        ('        *rng=saved;','        ++dfb_replays;\n        *rng=saved;')]:
        assert source.count(a)==1,a
        source=source.replace(a,b)
    header=(ROOT/'src/nbody_df_batch.h').read_text()
    hooks=[
        ('    DfbJob job[DFB_CAP];','    DFB_EVENT(evaluated,n);DFB_EVENT(batch,n);\n    DfbJob job[DFB_CAP];'),
        ('    real v[DFB_CAP],out[DFB_CAP];int n=0;','    for(int i=0;i<cache->n;++i)if(!cache->used[i])DFB_EVENT(wasted,1);\n    real v[DFB_CAP],out[DFB_CAP];int n=0;'),
        ('cache->used[i]=1;*d=cache->d[i];','cache->used[i]=1;*d=cache->d[i];DFB_EVENT(used,1);'),
        ('    return df8_less(p1,p2)?-p1:-p2;','    for(int i=0;i<cache.n;++i)if(!cache.used[i])DFB_EVENT(wasted,1);\n    return df8_less(p1,p2)?-p1:-p2;'),
        ('            if(df8_less(u,mw_fabs(dd[k]/maximum))) {return v;}','            DFB_EVENT(used,1);DFB_EVENT(attempts,1);\n            if(df8_less(u,mw_fabs(dd[k]/maximum))) {++dfb_attempt_histogram[counter+1];DFB_EVENT(wasted,n-k-1);return v;}'),
        ('            if(counter>1000){return 0;}','            if(counter>1000){++dfb_attempt_histogram[counter+1];DFB_EVENT(wasted,n-k-1);return 0;}')]
    for a,b in hooks:
        assert header.count(a)==1,a
        header=header.replace(a,b)
    write_changed(B/'s10_df_batch_instrumented.h',header.encode())
    source=source.replace('#include "nbody_df_batch.h"','#include "s10_df_batch_instrumented.h"')
    write_changed(B/(variant+'-capture.c'),source.encode())
    write_changed(B/'nbody_gen_profile.h',(u/'nbody/include/nbody_gen_profile.h').read_bytes())


def run(variant,case):
    assert variant in ['release','batch'] and case in ['core-small','real-steps']
    out=RUNS/(case+'-'+variant);out.mkdir(parents=True,exist_ok=True)
    exe=B/('x86-'+variant)/'capture.exe'
    cmd=[str(exe),'-f',str(ROOT/('workunits/'+case+'/params.lua')),
         '-h',str(ROOT/'workunits/core-small/OCS_data_2025_north_194.hist'),'-z',str(out/'histogram.txt'),
         '-c',str(out/'checkpoint'),'--seed','65477096','--nthreads','4','--print-histogram',
         '--ignore-checkpoint','--checkpoint-interval=-1','-np','14','-p']+old.ARGS
    env=dict(os.environ,OMP_NUM_THREADS='4',OMP_DYNAMIC='FALSE',S8_INITIAL_BODIES=str(out/'initial-bodies.bin'),S10_RNG_TRACE=str(out/'rng.bin'))
    # A host inherited card affinity would invalidate the four-thread measurement.
    env.pop('GOMP_CPU_AFFINITY',None);env.pop('OMP_PLACES',None);env.pop('OMP_PROC_BIND',None)
    save(out/'command.json',cmd);t=time.monotonic()
    with (out/'stdout.txt').open('w') as stdout,(out/'stderr.txt').open('w') as stderr:
        result=subprocess.run(cmd,cwd=out,env=env,stdout=stdout,stderr=stderr)
    seconds=time.monotonic()-t
    (out/'exit.txt').write_text(str(result.returncode)+'\n')
    assert result.returncode==0,(case,variant,result.returncode)
    text=(out/'stderr.txt').read_text()
    counts=dict(re.findall(r'(\w+)=(\d+)',re.search(r'DFB_COUNTS (.*)',text)[1]))
    row=dict(binary=rel(exe),binary_sha256=sha(exe),run=rel(out),threads=4,generation_seconds=float(re.search(r'S8_GENERATION_SECONDS=([\d.]+)',text)[1]),whole_seconds=seconds,
        rng_record_bytes=int(re.search(r'S10_RNG_RECORD_BYTES=(\d+)',text)[1]),counts={k:int(v) for k,v in counts.items()},likelihood_hex=compare.load_run(out)[0].hex())
    for key,marker in [('attempt_histogram','DFB_ATTEMPT_HIST'),('batch_histogram','DFB_BATCH_HIST')]:
        line=re.search(marker+r'([^\n]*)',text)
        row[key]={k:int(v) for k,v in re.findall(r'(\d+)=(\d+)',line[1])} if line else {}
    save(B/(case+'-'+variant+'.json'),row);print(json.dumps(row,indent=2),flush=True)

def proof():
    rows={}
    for case in ['core-small','real-steps']:
        exact,fast=[json.loads((B/(case+'-'+v+'.json')).read_text()) for v in ['release','batch']]
        a,b=[ROOT/x['run'] for x in [exact,fast]]
        different,first=old.file_differences(a/'initial-bodies.bin',b/'initial-bodies.bin',56)
        rng,first_rng=old.file_differences(a/'rng.bin',b/'rng.bin',exact['rng_record_bytes'])
        rows[case]=dict(reference=rel(a),experiment=rel(b),different_bodies=different,first_different_body=first,different_rng_states=rng,
            first_rng_divergence_body=first_rng,rng_record_bytes=exact['rng_record_bytes'],counts=fast['counts'],threads=4,
            exact_generation_seconds=exact['generation_seconds'],batch_generation_seconds=fast['generation_seconds'],
            exact_whole_seconds=exact['whole_seconds'],batch_whole_seconds=fast['whole_seconds'],
            attempt_histogram=fast.get('attempt_histogram',{}),batch_histogram=fast.get('batch_histogram',{}),
            likelihood_difference=compare.load_run(b)[0]-compare.load_run(a)[0])
    save(B/'proof.json',rows);print(json.dumps(rows,indent=2))

def stage():
    # Freeze these before any native run. The blocked twin cannot calibrate a forecast.
    prediction=dict(recorded_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        classification='uncalibrated hypotheses; card acceptance pending',
        hypothesis='More vector occupancy trades against speculative waste and root preparation. No speed gain or native equality is assumed.',
        core_small_seconds=[30,120],real_steps_seconds=[150,600],
        exact_reference='S10-09 card: core-small 54.3 s; real-steps 246.1 s',
        twin='See twin-results.json: unsupported results provide no cycle prediction')
    if not (B/'prediction.json').exists():save(B/'prediction.json',prediction)
    affinity=' '.join(str(i) for i in range(1,241))
    lines=['#!/usr/bin/env bash','# Lead only, in an authorized card window.','set -euo pipefail',
        'cd "$(dirname "$0")/../../.."','test -s build/s10/df-batch/prediction.json',
        'mkdir -p runs/card/s10-df-batch']
    for case in ['core-small','real-steps']:
        for variant in ['release','batch']:
            exe=B/('card-'+variant)/'milkyway_nbody.mic';label=variant+'-'+case+'-240'
            cmd=['python','tools/card_run','--benchmark','--threads','240','--transfer','tcp-large','--transport-timeout','300','--stage-timeout','600','--timeout','1800',
                '--receipt','runs/card/s10-df-batch/'+label+'.json','--file',rel(exe),'--file','workunits/'+case+'/params.lua','--file','workunits/core-small/OCS_data_2025_north_194.hist']
            for runtime in sorted((B/'runtimes').iterdir()):cmd+=['--file',rel(runtime)]
            binding=['GOMP_CPU_AFFINITY='+affinity,'OMP_PROC_BIND=TRUE','DF_BATCH_AFFINITY=1'] if variant=='batch' else []
            cmd+=['scripts/s10-df-batch-launch.sh','OMP_NUM_THREADS=240']+binding+['./milkyway_nbody.mic','-f','params.lua','-h','OCS_data_2025_north_194.hist',
                '--seed','65477096','--nthreads','240','--print-histogram','--ignore-checkpoint','--checkpoint-interval=-1','-np','14','-p']+old.ARGS
            lines+=['# SHA256 '+sha(exe),' '.join(shlex.quote(x) for x in cmd)+' > runs/card/s10-df-batch/'+label+'.txt 2>&1']
    lines+=['S10_REQUIRE_CARD=1 python tests/test_s10_df_batch.py']
    (B/'card-window.sh').write_bytes(('\n'.join(lines)+'\n').encode())
    files=[p for p in B.rglob('*') if p.is_file() and p.name!='handoff.json' and
        (p.suffix in ['.mic','.so','.1','.6','.su'] or p.name in ['prediction.json','card-window.sh','knc-lint.txt','.build-options'])]
    files += [B/name for name in ['proof.json','kernel.json','working-set.json','twin-results.json','library-provenance.json','compiler-items.txt','compiler-items.s']]
    files += [p for p in (B/'twin').rglob('*') if p.is_file() and p.suffix in ['.json','.bin']]
    files += [p for p in RUNS.rglob('*') if p.is_file()]
    files += [ROOT/name for name in ['mk/Makefile','config/release.env','patches/README.md','patches/zzzzzzzz-nbody-df-batch.patch',
        'src/nbody_df_batch.h','src/nbody_df_vector8.h','tests/s10-df-batch.mk','tests/s10_df_batch_kernel.c','tests/s10_df_batch_capture.h',
        'tests/test_s10_df_batch.py','scripts/s10-df-batch.py','scripts/build-s10-df-batch.sh','scripts/test-s10-df-batch.sh',
        'scripts/s10-df-batch-launch.sh','scripts/twin-s10-df-batch.py','scripts/model-s10-df-batch.py','docs/research/s10-df-batch.md']]
    save(B/'handoff.json',dict(files={rel(p):sha(p) for p in files}))

if __name__=='__main__':
    os.chdir(ROOT);B.mkdir(parents=True,exist_ok=True)
    globals()[sys.argv[1]](*sys.argv[2:])
