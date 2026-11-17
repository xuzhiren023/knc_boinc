"""Read capture ABI; independent binary64 oracle and field-line host counter."""
import bisect
import json
import math
from pathlib import Path
import re
import struct

def load_tree(prefix, layout_file):
    raw=json.loads(Path(str(prefix)+'.json').read_text())
    data=Path(str(prefix)+'.bin').read_bytes()
    text=layout_file.read_text(); text=text[text.index('s10_layout:'):]
    layout=[int(x,0) for x in re.findall(r'^\s*\.quad\s+([^\s]+)',text,re.M)]
    assert raw['layout']==layout[:12]
    blocks=sorted((int(b['addr'],0), data[b['offset']:b['offset']+b['length']]) for b in raw['blocks'] if b)
    starts=[a for a,_ in blocks]
    def get(addr,fmt):
        i=bisect.bisect_right(starts,addr)-1
        assert i>=0
        base,buf=blocks[i]
        return struct.unpack_from(fmt,buf,addr-base)[0]
    return raw,data,layout,get

def spatial_order(raw,l,get):
    q=get(int(raw['state'],0)+l[10],'<Q'); bodies=int(raw['bodies'],0)
    result=[]
    while q:
        cell=get(q+l[6],'<h')==0
        if not cell: result.append((q-bodies)//raw['body_bytes'])
        q=get(q+(l[8] if cell else l[5]),'<Q')
    # Zero mass bodies do not occur in tree; caller's legal fallback is generation order.
    assert sorted(result)==list(range(raw['nbody']))
    return result

def walk(raw,l,get,index):
    p=int(raw['bodies'],0)+index*raw['body_bytes']
    pos=[get(p+l[3]+8*j,'<d') for j in range(3)]
    pt=get(p+l[6],'<h'); ctx=int(raw['ctx'],0)
    eps=[get(ctx+l[11]+8*j,'<d') for j in range(3)]
    quad=get(ctx+l[12],'<B')!=0
    q=get(int(raw['state'],0)+l[10],'<Q'); a=[0.,0.,0.]; nodes=0;lines=set();seen=False
    def read(addr,fmt):
        lines.update(range(addr//64,(addr+struct.calcsize(fmt)-1)//64+1))
        return get(addr,fmt)
    while q:
        nodes+=1
        x,y,z=[read(q+l[3]+8*j,'<d')-pos[j] for j in range(3)]
        d=z*z+(y*y+x*x); typ=read(q+l[6],'<h')
        if typ or d>=read(q+l[7],'<d'):
            if q!=p:
                t=typ+pt; d+=eps[2 if t==-2 else 0 if t==2 else 1]
                r=math.sqrt(d); phi=read(q+l[4],'<d')/r;m=phi/d
                a[0]+=m*x;a[1]+=m*y;a[2]+=m*z
                if quad and not typ:
                    xx,xy,xz,yy,yz,zz=[read(q+l[9]+8*j,'<d') for j in range(6)]
                    qx=(xx*x+xy*y)+xz*z;qy=(xy*x+yy*y)+yz*z;qz=(xz*x+yz*y)+zz*z
                    dot=(qx*x+qy*y)+qz*z;inv=1./((d*d)*r);pq=(2.5*(inv*dot))/d
                    a[0]+=pq*x;a[1]+=pq*y;a[2]+=pq*z
                    a[0]-=inv*qx;a[1]-=inv*qy;a[2]-=inv*qz
            else: seen=True
            q=read(q+l[5],'<Q')
        else:q=read(q+l[8],'<Q')
    assert seen
    return a,nodes,lines
