"""Whole compiled nbGravity, repeated actual targets on 4 contexts or 8 tiles.

No stubs or instruction substitutions. Ring quantities stay in raw tool output;
the research report gives direction and stall causes only.
"""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from twin_s10_memory_common import load_tree, spatial_order, walk
ROOT=Path(__file__).resolve().parents[1]; B=ROOT/'build/s10-memory'; OUT=B/'twin'
HOME=Path('C:/Users/xuzhi/.claude/skills/knc-twin')
OD=Path('C:/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cross/bin/k1om-mpss-linux-objdump')
commands=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_bytes((json.dumps(x,indent=2)+'\n').encode())
def command(args,name):
    start=time.monotonic()
    with (OUT/(name+'.log')).open('w') as f:r=subprocess.run([str(x) for x in args],stdout=f,stderr=subprocess.STDOUT)
    row=dict(argv=list(map(str,args)),exit_code=r.returncode,host_seconds=time.monotonic()-start)
    commands.append(row);return row

def main():
    OUT.mkdir(exist_ok=True)
    prior=json.loads((OUT/'evidence.json').read_text()) if (OUT/'evidence.json').exists() else {}
    commands.extend(prior.get('commands',[]))
    assert (B/'model.json').exists(), 'model first'
    # Capabilities inspected before constructing any kernels.
    command([sys.executable,HOME/'scripts/knc_twin.py','capabilities','--out',OUT/'capabilities','--force'],'capabilities')
    inventory=json.loads((OUT/'capabilities/capabilities.json').read_text())
    assert all(s in inventory['scales'] for s in ('core','ring'))
    raw,data,l,get=load_tree(B/'capture-base',B/'layout-card.s')
    assert l==load_tree(B/'capture-base',B/'layout-x86.s')[2], 'host/card ABI differs'
    binary=B/'card-base/milkyway_nbody.mic'
    adapter=OUT/'adapter.json'
    row=command([sys.executable,HOME/'scripts/from_binary.py',binary,'--function','nbGravity','--objdump',OD,
        '--out',adapter,'--report',OUT/'coverage.json'],'adapter')
    assert row['exit_code']==0
    full=json.loads(adapter.read_text()); ins=full['streams'][0]['instructions']
    order=spatial_order(raw,l,get)
    evidence=dict(prior_attempts=['initial-two-call-attempt/','full-background-one-call/'],model_table_used=True,commands=commands,runs={},profile='card-7120-measured',snapshot_sha256=sha(B/'capture-base.bin'))
    for scale in ('core','ring'):
        contexts=4 if scale=='core' else 32
        ncall=2 if scale=='core' else 1
        # Matched generation-random targets distributed across the full body
        # range. Sorting this same set by DFS tests spatial order without
        # changing the interaction mix. Ring uses disjoint target chunks.
        selected=set(range(0,raw['nbody'],raw['nbody']//(contexts*ncall)))
        selected=set(sorted(selected)[:contexts*ncall])
        sequences={'random':sorted(selected),'spatial':[i for i in order if i in selected]}
        assert all(len(s)==contexts*ncall for s in sequences.values())
        for name,seq in sequences.items():
            key=scale+'-'+name
            kernel=copy.deepcopy(full)
            memory=kernel.get('init',{}).get('memory',[])
            memory += [dict(addr=b['addr'],hex=data[b['offset']:b['offset']+b['length']].hex()) for b in raw['blocks'] if b]
            kernel['init']['memory']=memory;kernel['init']['registers']={}
            kernel['streams']=[];expected=[]
            # Core uses two-body chunks; ring one body per sibling. The application uses
            # four-body chunks; this bounded sample tests shared-cache direction
            # without claiming to simulate a full force map or caller overhead.
            for t in range(contexts):
                core=t//4; sibling=t%4
                targets=[seq[core*4*ncall+sibling*ncall+j] for j in range(ncall)]
                regs=[]
                for j,index in enumerate(targets):
                    out=0x600000000+t*4096+j*64
                    regs.append(dict(registers=dict(rdi=hex(out),rsi=raw['ctx'],rdx=raw['state'],
                        rcx=hex(int(raw['bodies'],0)+index*raw['body_bytes']))))
                    acc,_,_=walk(raw,l,get,index)
                    import struct
                    expected.append(dict(addr=hex(out),hex=struct.pack('<3d',*acc).hex()))
                stream=dict(context=t%4,init=dict(registers={}),calls_table=regs,instructions=copy.deepcopy(ins))
                if scale=='ring':stream['core']=core
                kernel['streams'].append(stream)
            kernel.pop('memory_default',None)
            kernel['entry']='function'
            kernel['expected']=dict(memory=expected)
            kernel['scenario']=dict(memory=dict(type='line_tracking',cold_level='memory'),branch=dict(type='all_predicted'))
            if scale=='ring':kernel['scenario']['multicore']=dict(max_events=8000000,background=dict(enabled=False,active_cores=8))
            kernel['numerical_policy']=dict(rounding='rn',ftz=False,daz=False,x87_control_word='0x027f')
            kernel['unit_of_work']=dict(count=contexts*ncall,description=('two complete nbGravity calls per context on captured initial large tree' if ncall==2 else 'one complete nbGravity call per context on captured initial large tree'))
            kernel['provenance']['s10_07']=dict(binary_sha256=sha(binary),snapshot_sha256=sha(B/'capture-base.bin'),
                targets=seq,whole_function=True,caller='Argument setup and permutation/static scheduling excluded; paired matched target set.')
            path=OUT/(key+'-kernel.json')
            old_hash=sha(path) if path.exists() else None
            save(path,kernel)
            if old_hash==sha(path) and prior.get('runs',{}).get(key,{}).get('status')=='ok':
                evidence['runs'][key]=prior['runs'][key]
                print(key,'reused identical successful kernel',flush=True)
                continue
            cmd=command([sys.executable,HOME/'scripts/knc_twin.py','simulate',path,'--profile','card-7120-measured','--scale',scale,
                '--max-seconds','1800','--max-steps','4000000','--no-issue-log','--out',OUT/key,'--force'],key)
            result=json.loads((OUT/key/'result.json').read_text())
            row={k:result.get(k) for k in ('status','functional_check','assumptions','unsupported','limiting_constraints','calibration_status','parameters_used','python_execution_seconds')}
            row.update(contexts=contexts,calls_per_context=ncall,whole_function=True,binary_sha256=sha(binary),host_seconds=cmd['host_seconds'],result_path=str((OUT/key/'result.json').relative_to(ROOT)),
                result_class=result.get('result_class',(result.get('prediction') or {}).get('result_class')))
            if scale=='core' and result['status']=='ok':row['prediction']=result['prediction']
            evidence['runs'][key]=row;evidence['host_seconds']=sum(c['host_seconds'] for c in commands);save(OUT/'evidence.json',evidence)
            print(key,row['status'],row['result_class'],flush=True)
        if all(evidence['runs'][scale+'-'+n]['status']=='ok' for n in ('random','spatial')):
            command([sys.executable,HOME/'scripts/knc_twin.py','compare',OUT/(scale+'-random/result.json'),OUT/(scale+'-spatial/result.json'),
                '--out',OUT/(scale+'-compare'),'--force'],scale+'-compare')
    evidence['host_seconds']=sum(c['host_seconds'] for c in commands);save(OUT/'evidence.json',evidence)
if __name__=='__main__':main()
