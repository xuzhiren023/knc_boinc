"""S10-02 host proof, real profile reduction, assembly audit and card handoff."""
import hashlib
from datetime import datetime, timezone
import json
import math
import os
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
B = ROOT/'build/s10-walk'
RUNS = ROOT/'runs/s10-walk'
VARIANTS = ('base','prefetch','hot','both','profile4','profile1','guided')
SHARED = Path('C:/Users/xuzhi/Documents/gcc_knc/.work/_shared')
OBJDUMP = SHARED/'toolchain/cross/bin/k1om-mpss-linux-objdump'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def save(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes((json.dumps(value, indent=2)+'\n').encode())

def phase(run, name='nbMapForceBody'):
    text = compare.captured_output(run)
    return float(re.search(r'^PHASE '+name+r' (\S+) \d+$',text,re.M)[1])

def profiles(text):
    pattern=r'^WALK_PROFILE step=(\d+) thread=(\d+) team=(\d+) bodies=(\d+) nodes=(\d+) interactions=(\d+) cells=(\d+) walk=(\S+) active=(\S+)$'
    maps=[]
    for values in re.findall(pattern,text,re.M):
        step,thread,team,bodies,nodes,hits,cells=map(int,values[:7])
        if thread==0: maps.append([])
        maps[-1].append(dict(step=step,thread=thread,team=team,bodies=bodies,nodes=nodes,
                             interactions=hits,cells=cells,walk=float(values[7]),active=float(values[8])))
    assert maps, 'no profile rows'
    stats=[]
    for rows in maps:
        assert [r['thread'] for r in rows]==list(range(rows[0]['team']))
        row={k:sum(r[k] for r in rows) for k in ('nodes','interactions','cells','bodies','walk','active')}
        row['walk_max']=max(r['walk'] for r in rows)
        row['active_max']=max(r['active'] for r in rows)
        row['nonwalk_mean']=(row['active']-row['walk'])/len(rows)
        for key in ('nodes','interactions','walk','active'):
            values=[r[key] for r in rows]; mean=statistics.mean(values)
            row[key+'_max_mean']=max(values)/mean if mean else 0
            row[key+'_cv']=statistics.pstdev(values)/mean if mean else 0
        stats.append(row)
    team=maps[0][0]['team']
    assert all(len(rows)==team for rows in maps), 'team size changed between maps'
    totals=[dict(thread=i,**{k:sum(rows[i][k] for rows in maps) for k in
        ('nodes','interactions','cells','bodies','walk','active')}) for i in range(team)]
    return dict(thread_totals=totals,maps=len(maps),threads=team,
        **{k:sum(r[k] for r in stats) for k in ('nodes','interactions','cells','bodies')},
        max_mean_work=max(r['nodes_max_mean'] for r in stats), per_map=stats)

def proof():
    harness.RUNS=RUNS
    evidence=dict(binaries={},runs={})
    progress=B/'proof-progress.json'
    prior=json.loads(progress.read_text(encoding='utf-8')) if progress.exists() else dict(binaries={},runs={})
    logs=[]
    refs={case:harness.copy_reference(case) for case in ('small','medium','large')}
    force_refs={}
    for case in refs:
        source=ROOT.parent/'S8-08/build/s8'/('walk-reference-x86-%s-1-forces.bin'%case)
        source12=source.with_name(source.name.replace('-1-forces','-12-forces'))
        assert sha(source)==sha(source12), 'prior scalar force reference differs by threads'
        dest=refs[case]/'forces.bin';shutil.copyfile(source,dest)
        force_refs[case]=dest
        save(refs[case]/'force-provenance.json',dict(source=str(source),sha256=sha(source),same_at_1_and_12_threads=True))
    for variant in VARIANTS:
        exe=B/('x86-'+variant+'/milkyway_nbody.exe')
        evidence['binaries'][variant]=sha(exe)
        cases=('small','medium','large') if variant in ('prefetch','hot','both') else ('large',)
        for case in cases:
            thread_counts=(12,) if variant in ('profile4','profile1','guided') else (1,12)
            for threads in thread_counts:
                label='%s-%s-t%d'%(variant,case,threads)
                out=RUNS/label; out.mkdir(parents=True,exist_ok=True)
                env={'NBODY_WALK_FORCE_DUMP':str(out/'forces.bin'),
                     'OMP_WAIT_POLICY':'PASSIVE','GOMP_SPINCOUNT':'0'}
                if case=='large' and threads==1 and variant in ('base','prefetch','hot','both'):
                    env['NBODY_WALK_CAPTURE']=str(B/('proof-capture-'+variant))
                retained=prior['runs'].get(label)
                reuse=(retained and prior['binaries'].get(variant)==sha(exe) and
                       (out/'exit.txt').exists() and (out/'exit.txt').read_text(encoding='utf-8').strip()=='0' and
                       (out/'forces.bin').exists() and sha(out/'forces.bin')==retained['force_sha256'])
                if 'NBODY_WALK_CAPTURE' in env:
                    reuse=reuse and all(Path(env['NBODY_WALK_CAPTURE']+suffix).exists() for suffix in ('.json','.bin'))
                run=out if reuse else harness.run(exe,case,threads,label,env)
                wait_policy=retained.get('wait_policy','runtime default') if reuse else 'PASSIVE; GOMP_SPINCOUNT=0'
                ref=refs[case]
                result=subprocess.check_output([sys.executable,ROOT/'scripts/compare.py',ref,run],text=True)
                assert json.dumps(compare.load_run(ref),sort_keys=True)==json.dumps(compare.load_run(run),sort_keys=True),label
                force_ref=force_refs[case]
                assert (run/'forces.bin').read_bytes()==force_ref.read_bytes(), 'force bits: '+label
                calls=int(re.search(r'^PHASE nbMapForceBody \S+ (\d+)$',compare.captured_output(run),re.M)[1])
                nbody=dict(small=64,medium=1024,large=20000)[case]
                assert (run/'forces.bin').stat().st_size==calls*nbody*24,label
                evidence['runs'][label]=dict(run=run.relative_to(ROOT).as_posix(),reference=ref.relative_to(ROOT).as_posix(),
                    force_reference=force_ref.relative_to(ROOT).as_posix(),force_sha256=sha(run/'forces.bin'),compare=result,
                    wait_policy=wait_policy,maps=calls,force_seconds=phase(run),whole_seconds=phase(run,'whole_run'))
                line='%s: force xyz bytes PASS (%d maps); %s'%(label,calls,result.strip())
                print(line,flush=True); logs.append(line)
                save(B/'proof-progress.json',evidence)
    save(B/'proof.json',evidence)
    (B/'proof.txt').write_bytes(('\n'.join(logs)+'\n').encode())
    save(B/'profiles.json',{v:profiles(compare.captured_output(RUNS/(v+'-large-t12'))) for v in ('profile4','profile1','guided')})

def rank():
    harness.RUNS=RUNS
    rows={v:[] for v in ('base','prefetch','hot','both')}
    # Three interleaved full runs with force dumps/capture disabled. Proof I/O
    # is charged to NB_FORCE, so never mix proof samples into this ranking.
    for repeat in (0,1,2):
        order=('both','hot','prefetch','base') if repeat==1 else ('base','hot','both','prefetch')
        for v in order:
            run=harness.run(B/('x86-'+v+'/milkyway_nbody.exe'),'large',12,'rank-%s-%d'%(v,repeat))
            rows[v].append(dict(force=phase(run),whole=phase(run,'whole_run'),run=str(run.relative_to(ROOT))))
    value={v:dict(samples=s,force_median=statistics.median(r['force'] for r in s),
                 force_range=[min(r['force'] for r in s),max(r['force'] for r in s)],
                 whole_median=statistics.median(r['whole'] for r in s)) for v,s in rows.items()}
    value['_runtime']=dict(OMP_WAIT_POLICY=os.environ.get('OMP_WAIT_POLICY','runtime default'),
        GOMP_SPINCOUNT=os.environ.get('GOMP_SPINCOUNT','runtime default'),threads=12,OMP_DYNAMIC='FALSE',
        limitation='Contended host: unrelated compute processes observed; provisional rank only.')
    save(B/'host-ranking.json',value)
    print(json.dumps(value,indent=2),flush=True)

def assembly():
    result={'functions':{}}
    binary=B/'card-base/milkyway_nbody.mic'
    text=subprocess.check_output([str(OBJDUMP),'-dr',str(binary)],text=True)
    symbols=subprocess.check_output([str(OBJDUMP),'-t',str(binary)],text=True)
    bounds={}
    for line in symbols.splitlines():
        m=re.match(r'^([0-9a-f]+)\s+\w+\s+F\s+\S+\s+([0-9a-f]+)\s+(\S+)$',line)
        if m:bounds[m[3]]=(int(m[1],16),int(m[1],16)+int(m[2],16))
    funcs={}; name=None
    for line in text.splitlines():
        m=re.match(r'^([0-9a-f]+) <([^>]+)>:',line)
        if m: name=m[2];funcs[name]=[]
        elif name: funcs[name].append(line)
    for name in ('nbGravity','nbMapForceBody._omp_fn.0','nbGravMap'):
        lines=funcs[name]; dis='\n'.join(lines)+'\n'
        (B/(name+'.dis')).write_bytes(dis.encode())
        ins=[]
        for line in lines:
            m=re.match(r'^\s*([0-9a-f]+):\s+(?:[0-9a-f]{2}\s+)+\s*([a-z][a-z0-9]*)\s*(.*)$',line)
            if m and bounds[name][0]<=int(m[1],16)<bounds[name][1]:ins.append((m[1],m[2],m[3]))
        result['functions'][name]=dict(symbol_start=hex(bounds[name][0]),symbol_end=hex(bounds[name][1]),instructions=len(ins),fxch=sum(op=='fxch' for _,op,arg in ins),
            stack_fp=sum(op.startswith('f') and bool(re.search(r'\(%(?:rsp|rbp)\)',arg)) for _,op,arg in ins),
            fp_memory=sum(op.startswith('f') and '(' in arg and '%st' not in arg for _,op,arg in ins),
            div=sum(op.startswith('fdiv') for _,op,arg in ins),sqrt=sum(op=='fsqrt' for _,op,arg in ins),
            branches=[dict(addr=a,op=op,arg=arg) for a,op,arg in ins if op.startswith('j')],
            calls=[dict(addr=a,arg=arg) for a,op,arg in ins if op.startswith('call')])
    result['binary_sha256']=sha(binary)
    save(B/'assembly.json',result)

def stage():
    predictions={
        'base':'Existing S9-06 force 12.70 s; whole 15.89 s. Repeat/drift control.',
        'profile4':'Force scenario 12.1-16.5 s including unknown profile cost. Work sum must equal baseline counts; balance unknown.',
        'profile1':'Force scenario 12.1-16.5 s. Smaller tail may offset more contended dispatches; no winner assumed.',
        'guided':'Force scenario 12.1-16.5 s. Less dispatch, possible larger tail; no winner assumed.',
        'prefetch':'Force scenario 11.4-14.6 s; whole 14.6-17.8 s. Extra hints may lose.',
        'hot':'Force scenario 11.4-14.0 s; whole 14.6-17.2 s. Reduced hot field span; cache placement unknown.',
        'both':'Force scenario 10.8-15.2 s; whole 14.0-18.4 s. Effects need not add.'}
    lines=['#!/usr/bin/env bash','# Lead only, authorized card window. Predictions frozen in card-manifest.json.',
        'set -euo pipefail','cd "$(dirname "$0")/../.."','mkdir -p runs/card/s10-walk']
    jobs=[]
    for variant,case in [(v,'large') for v in VARIANTS]+[('both','core-small')]:
        binary=B/('card-'+variant+'/milkyway_nbody.mic')
        hist='OCS_data_2025_north_194.hist' if case=='core-small' else 'input.hist'
        label=variant+'-'+case
        args=harness.arguments(case,240);args[1]='params.lua';args[3]=hist
        args=['-z','claude-histogram.txt','-c','claude-checkpoint']+args
        command=['python','tools/card_run','--benchmark','--threads','240','--timeout','900',
            '--receipt','runs/card/s10-walk/'+label+'.json',
            '--collect','claude-stderr.txt','--collect','claude-histogram.txt',
            '--collect-dir','runs/card/s10-walk/'+label,
            '--file',str(binary.relative_to(ROOT).as_posix()),
            '--file','workunits/'+case+'/params.lua','--file','workunits/'+case+'/'+hist]
        for lib in ('libgomp.so.1','libstdc++.so.6','libgcc_s.so.1'):
            command+=['--file','build/s10-walk/runtimes/'+lib]
        command+=['scripts/s10-walk-launch.sh']+args
        lines.append(' '.join(shlex.quote(x) for x in command)+' > runs/card/s10-walk/'+label+'.txt 2>&1')
        pred=predictions[variant] if case=='large' else 'S9-06 same-option prior: whole 63.410 s, force 0.1883 s. Expect whole about 63.4 s (scenario 60-67 s), force 0.15-0.23 s; no material whole-run gain predicted.'
        jobs.append(dict(variant=variant,case=case,binary=binary.relative_to(ROOT).as_posix(),binary_sha256=sha(binary),
            prediction=pred,classification='engineering scenario; not a calibrated forecast',measured=None))
    (B/'window.sh').write_bytes(('\n'.join(lines)+'\n').encode())
    files=sorted((ROOT/'patches').glob('*.patch'))+sorted((ROOT/'src').glob('nbody_walk*.h'))
    files+=sorted((B/'runtimes').iterdir())+[B/'window.sh',ROOT/'docs/research/s10-force-walk.md',ROOT/'scripts/s10-walk-launch.sh',ROOT/'mk/Makefile',ROOT/'mk/sources.mk']
    files+=list((ROOT/'workunits/large').glob('*'))+list((ROOT/'workunits/core-small').glob('*'))
    files+=[B/('card-'+v+'/.build-options') for v in VARIANTS]
    files+=sorted((ROOT/'scripts').glob('*s10*'))+sorted((ROOT/'probes').glob('s10*'))
    files+=sorted((B/'twin').glob('*/result.json'))+[B/'twin/evidence.json',B/'proof.json',B/'host-ranking.json']
    files+=sorted(B.glob('capture-*-provenance.json'))
    files+=sorted((B/'prior').glob('*'))
    twin=json.loads((B/'twin/evidence.json').read_text(encoding='utf-8')) if (B/'twin/evidence.json').exists() else None
    save(B/'card-manifest.json',dict(twin=twin,recorded_at=datetime.now(timezone.utc).isoformat(),option_source='S9-06 fallback; S10-01 release.env absent',jobs=jobs,
         files={p.relative_to(ROOT).as_posix():sha(p) for p in files if p.is_file()}))
    (B/'predictions.txt').write_bytes(('Recorded before card execution. No measured values.\n'+'\n'.join('%s %s: %s'%(r['variant'],r['case'],r['prediction']) for r in jobs)+'\n').encode())
    print('Staged eight jobs; no card command executed.',flush=True)

def analyze_card():
    # card_run stdout includes the application's captured stderr. Accept explicit
    # extracted stderr paths too, without guessing timings out of receipts.
    files=[Path(x).resolve() for x in sys.argv[2:]] or sorted((ROOT/'runs/card/s10-walk').glob('*.txt'))
    result={str(p.relative_to(ROOT)):profiles(p.read_text(encoding='utf-8',errors='replace')) for p in files if 'WALK_PROFILE step=' in p.read_text(encoding='utf-8',errors='replace')}
    assert result,'No WALK_PROFILE rows found: supply extracted application stderr paths.'
    save(B/'card-profiles.json',result)
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    {'proof':proof,'rank':rank,'assembly':assembly,'stage':stage,'analyze-card':analyze_card}[sys.argv[1]]()
