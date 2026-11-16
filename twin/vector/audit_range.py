"""Audit every binary64 intermediate of the captured 4096 scalar walks."""
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
root=Path('twin/vector'); source=root/'capture'
a=(source/'layout-x86.bin').read_bytes(); b=(source/'layout-card.bin').read_bytes()
assert a[:176]==b[:176]
layout=struct.unpack('<22Q',a[:176])
_,_,_,ctxsize,statesize,_,bodysize,_,ceps,csize,cmin,cquad,stree,_,npos,nnext,nmass,ntype,bindex,crit,more,qoff=layout
cap=json.loads((root/'capture.json').read_text());cache={};nodes={}
for block in cap['init']['memory']:
    if 'file' not in block: continue
    name=block['file']
    if name not in cache: cache[name]=(root/name).read_bytes()
    data=cache[name]; offset=block.get('offset',0); data=data[offset:offset+block.get('length',len(data))]
    if name=='capture/nodes.bin': nodes[int(block['addr'],0)]=data
ctx=cache['capture/ctx.bin'];st=cache['capture/state.bin'];bodies=cache['capture/bodies.bin']
def u64(b,o): return struct.unpack_from('<Q',b,o)[0]
def dbl(b,o): return struct.unpack_from('<d',b,o)[0]
def idx(b,o): return struct.unpack_from('<i',b,o)[0]
soft=struct.unpack('<%dd'%(len(cache['capture/eps2.bin'])//8),cache['capture/eps2.bin'])
size=u64(ctx,csize);minimum=dbl(ctx,cmin);usequad=ctx[cquad]!=0
bodybase=int(cap['init']['registers']['rcx'],0);tree=u64(st,stree)
lo=math.inf;hi=0.;count=0;subnormal=0;nonfinite=0
# Recording every primitive catches underflow in intermediate products too.
def record(x):
    global lo,hi,count,subnormal,nonfinite
    count+=1
    if not math.isfinite(x): nonfinite+=1
    elif x:
        v=abs(x);lo=min(lo,v);hi=max(hi,v);subnormal+=v<sys.float_info.min
    return x
def add(a,b): return record(a+b)
def sub(a,b): return record(a-b)
def mul(a,b): return record(a*b)
def div(a,b): return record(a/b)
expected=(root/'capture/expected.bin').read_bytes();actual=bytearray();visits=[]
for i in range(4096):
    p=bodies[i*bodysize:(i+1)*bodysize];pos=struct.unpack_from('<3d',p,npos);pi=idx(p,bindex)
    q=tree;acc=[0.,0.,0.];seen=False;n=0
    while q:
        n+=1;node=nodes[q];kind=struct.unpack_from('<h',node,ntype)[0]
        xyz=struct.unpack_from('<3d',node,npos)
        dr=[sub(xyz[j],pos[j]) for j in range(3)]
        d=add(mul(dr[2],dr[2]),add(mul(dr[1],dr[1]),mul(dr[0],dr[0])))
        if kind or d>=dbl(node,crit):
            if q!=bodybase+i*bodysize:
                d=add(d,minimum if not kind else soft[idx(node,bindex)*size+pi])
                r=record(math.sqrt(d));m=div(div(dbl(node,nmass),r),d)
                for j in range(3): acc[j]=add(acc[j],mul(m,dr[j]))
                if usequad and not kind:
                    xx,xy,xz,yy,yz,zz=struct.unpack_from('<6d',node,qoff)
                    mat=((xx,xy,xz),(xy,yy,yz),(xz,yz,zz))
                    v=[add(add(mul(row[0],dr[0]),mul(row[1],dr[1])),mul(row[2],dr[2])) for row in mat]
                    dot=add(add(mul(v[0],dr[0]),mul(v[1],dr[1])),mul(v[2],dr[2]))
                    inv=div(1.,mul(mul(d,d),r));phi=div(mul(2.5,mul(inv,dot)),d)
                    for j in range(3): acc[j]=add(acc[j],mul(phi,dr[j]))
                    for j in range(3): acc[j]=sub(acc[j],mul(inv,v[j]))
            else: seen=True
            q=u64(node,nnext)
        else: q=u64(node,more)
    assert seen
    visits.append(n);actual.extend(struct.pack('<3d',*acc))
assert actual==expected
result={'bodies':4096,'primitive_operations':count,'subnormal_results':subnormal,'nonfinite_results':nonfinite,
        'min_nonzero_abs':lo,'max_abs':hi,'expected_xyz_sha256':hashlib.sha256(actual).hexdigest(),
        'scope':'first large force step only; Python binary64 scalar order, independently matched to all captured XYZ bytes',
        'group_visits':{str(first):visits[first:first+8] for first in (0,1024)}}
(root/'range.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
