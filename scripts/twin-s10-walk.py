"""Complete card nbGravity, bound to each variant's real captured large tree.

Same cold-memory/all-predicted-branches scenario, four actual target bodies.
No callee stubs, instruction replacement, reciprocal tables or cross-card scale.
"""
import copy
import bisect
import math
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
B=ROOT/'build/s10-walk'
OUT=B/'twin'
HOME=Path('C:/Users/xuzhi/.claude/skills/knc-twin')
OD=Path('C:/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cross/bin/k1om-mpss-linux-objdump')
sys.dont_write_bytecode=True

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x): p.write_bytes((json.dumps(x,indent=2)+'\n').encode())
commands=[]
def command(args,log):
    start=time.monotonic()
    with log.open('w') as f:
        r=subprocess.run([str(x) for x in args],stdout=f,stderr=subprocess.STDOUT)
    row=dict(argv=[str(x) for x in args],exit_code=r.returncode,host_seconds=time.monotonic()-start)
    commands.append(row)
    return row

def offsets(path):
    text=path.read_text(encoding='utf-8');text=text[text.index('s10_layout:'):]
    # GCC emits each LP64 unsigned long as a quad; accept the 32-bit split form too.
    values=[int(x,0) for x in re.findall(r'^\s*\.quad\s+([^\s]+)',text,re.M)]
    if not values:
        values=[int(x,0) for x in re.findall(r'^\s*\.long\s+([^\s]+)',text,re.M)]
    return values

def oracle(raw,data,layout,index):
    # Independent binary64 host evaluation of the unmodified source grouping.
    blocks=sorted((int(b['addr'],0),data[b['offset']:b['offset']+b['length']]) for b in raw['blocks'] if b)
    starts=[a for a,_ in blocks]
    def get(addr,fmt):
        i=bisect.bisect_right(starts,addr)-1
        assert i>=0
        base,buf=blocks[i]; return struct.unpack_from(fmt,buf,addr-base)[0]
    def real(addr): return get(addr,'<d')
    p=int(raw['bodies'],0)+index*raw['body_bytes']
    pos=[real(p+layout[3]+8*j) for j in range(3)]
    ptype=get(p+layout[6],'<h'); ctx=int(raw['ctx'],0)
    eps=[real(ctx+layout[11]+8*j) for j in range(3)]
    quad=get(ctx+layout[12],'<B')!=0
    q=get(int(raw['state'],0)+layout[10],'<Q')
    a=[0.,0.,0.];seen=False;visits=hits=0
    while q:
        visits+=1
        x,y,z=[real(q+layout[3]+8*j)-pos[j] for j in range(3)]
        d=z*z+(y*y+x*x); typ=get(q+layout[6],'<h')
        if typ or d>=real(q+layout[7]):
            if q!=p:
                hits+=1; t=typ+ptype
                d+=eps[2 if t==-2 else 0 if t==2 else 1]
                r=math.sqrt(d); phi=real(q+layout[4])/r; m=phi/d
                a[0]+=m*x;a[1]+=m*y;a[2]+=m*z
                if quad and not typ:
                    xx,xy,xz,yy,yz,zz=[real(q+layout[9]+8*j) for j in range(6)]
                    qx=(xx*x+xy*y)+xz*z;qy=(xy*x+yy*y)+yz*z;qz=(xz*x+yz*y)+zz*z
                    dot=(qx*x+qy*y)+qz*z
                    inv=1.0/((d*d)*r);pq=(2.5*(inv*dot))/d
                    a[0]+=pq*x;a[1]+=pq*y;a[2]+=pq*z
                    a[0]-=inv*qx;a[1]-=inv*qy;a[2]-=inv*qz
            else: seen=True
            q=get(q+layout[5],'<Q')
        else:q=get(q+layout[8],'<Q')
    assert seen,'captured target did not encounter self'
    return dict(acceleration=a,nodes=visits,interactions=hits)

def main():
    OUT.mkdir(exist_ok=True)
    cap=command([sys.executable,HOME/'scripts/knc_twin.py','capabilities','--out',OUT/'capabilities','--force'],OUT/'capabilities.log')
    assert cap['exit_code']==0
    inventory=json.loads((OUT/'capabilities/capabilities.json').read_text(encoding='utf-8'))
    assert 'core' in inventory['scales']
    evidence=dict(commands=commands,variants={},model_table_used=True,profile='card-7120-measured',contexts=4,scale='core')
    for variant in ('base','prefetch','hot','both'):
        hot=int(variant in ('hot','both'))
        raw=json.loads((B/('capture-'+variant+'.json')).read_text(encoding='utf-8'))
        data=(B/('capture-'+variant+'.bin')).read_bytes()
        layout=offsets(B/('layout-x86-%d.s'%hot))
        assert layout==offsets(B/('layout-card-%d.s'%hot)), 'host/card ABI mismatch'
        assert raw['layout']==layout[:12], 'capture ABI mismatch'
        binary=B/('card-'+variant+'/milkyway_nbody.mic')
        full=OUT/(variant+'-adapter.json')
        converted=command([sys.executable,HOME/'scripts/from_binary.py',binary,'--function','nbGravity','--objdump',OD,
            '--out',full,'--report',OUT/(variant+'-coverage.json')],OUT/(variant+'-adapter.log'))
        assert converted['exit_code']==0, 'adapter failed; retained log is authoritative'
        kernel=json.loads(full.read_text(encoding='utf-8'))
        instructions=kernel['streams'][0]['instructions']
        memory=kernel.get('init',{}).get('memory',[])
        memory += [dict(addr=b['addr'],hex=data[b['offset']:b['offset']+b['length']].hex()) for b in raw['blocks'] if b]
        kernel['init']['memory']=memory
        kernel['init']['registers']={}
        kernel['streams']=[dict(context=i,init=dict(registers=dict(rdi=hex(0x60000000+i*4096),rsi=raw['ctx'],rdx=raw['state'],
            rcx=hex(int(raw['bodies'],0)+i*raw['body_bytes']))),instructions=copy.deepcopy(instructions)) for i in range(4)]
        kernel.pop('memory_default',None)
        references=[oracle(raw,data,layout,i) for i in range(4)]
        save(OUT/(variant+'-oracle.json'),references)
        kernel['expected']=dict(memory=[dict(addr=hex(0x60000000+i*4096),hex=struct.pack('<3d',*r['acceleration']).hex()) for i,r in enumerate(references)])
        kernel['scenario']=dict(memory=dict(type='line_tracking',cold_level='memory'),branch=dict(type='all_predicted'))
        kernel['numerical_policy']=dict(rounding='rn',ftz=False,daz=False,x87_control_word='0x027f')
        kernel['unit_of_work']=dict(count=4,description='four nbGravity calls on initial actual large tree, one target/context')
        kernel['provenance']['s10_02']=dict(binary_sha256=sha(binary),snapshot_sha256=sha(B/('capture-'+variant+'.bin')),
            snapshot_metadata_sha256=sha(B/('capture-'+variant+'.json')),layout=raw['layout'],whole_function=True,
            expected='Independent Python binary64 source-order oracle on the captured tree; separate whole-run x86 force-byte proof.')
        path=OUT/(variant+'-kernel.json');save(path,kernel)
        result_dir=OUT/(variant+'-simulate')
        run=command([sys.executable,HOME/'scripts/knc_twin.py','simulate',path,'--profile','card-7120-measured','--scale','core',
            '--max-seconds','55','--max-steps','1000000','--no-issue-log','--out',result_dir,'--force'],OUT/(variant+'-simulate.log'))
        result=json.loads((result_dir/'result.json').read_text(encoding='utf-8'))
        row={key:result.get(key) for key in ('status','result_class','assumptions','unsupported','limiting_constraints','calibration_status','parameters_used')}
        row['result_class']=result.get('result_class',(result.get('prediction') or {}).get('result_class'))
        row['prediction']=result.get('prediction') if result['status']=='ok' else None
        row['functional_check']=result.get('functional_check')
        row['python_execution_seconds']=result.get('python_execution_seconds')
        row.update(adapter_status='ok',binary_sha256=sha(binary),snapshot_sha256=sha(B/('capture-'+variant+'.bin')),
            host_seconds=run['host_seconds'],result_path=str((result_dir/'result.json').relative_to(ROOT)))
        evidence['variants'][variant]=row
        evidence['host_seconds']=sum(r['host_seconds'] for r in commands)
        save(OUT/'evidence.json',evidence)
        print(variant,row['status'],row['result_class'],flush=True)
    # Compare only successful predictions with unchanged model/scenario.
    for variant in ('prefetch','hot','both'):
        if all(evidence['variants'][v]['status']=='ok' for v in ('base',variant)):
            command([sys.executable,HOME/'scripts/knc_twin.py','compare',OUT/'base-simulate/result.json',OUT/(variant+'-simulate/result.json'),
                '--out',OUT/(variant+'-compare'),'--force'],OUT/(variant+'-compare.log'))
    evidence['host_seconds']=sum(r['host_seconds'] for r in commands)
    save(OUT/'evidence.json',evidence)
if __name__=='__main__': main()
