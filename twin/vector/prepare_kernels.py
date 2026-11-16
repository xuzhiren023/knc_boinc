"""Faithful full vector kernel; scalar compiled chunk keeps S1-07's cold cut."""
import copy
import os
import json
from pathlib import Path
root=Path('twin/vector')
cap=json.loads((root/'capture.json').read_text())
cache={}
filtered=[]
body_bytes=(root/'capture/bodies.bin').read_bytes()
body_base=int(cap['init']['registers']['rcx'],0)
for block in cap['init']['memory']:
    if 'offset' not in block:
        filtered.append(block)
        continue
    name=block['file']
    if name not in cache: cache[name]=(root/name).read_bytes()
    offset=block['offset'];length=block['length']
    data=cache[name][offset:offset+length]
    address=int(block['addr'],0)
    if body_base<=address<body_base+len(body_bytes):
        start=address-body_base
        assert data==body_bytes[start:start+length]
        continue
    # Exact captured node bytes inline avoid thousands of redundant file opens.
    filtered.append({'addr':block['addr'],'hex':data.hex()})
cap['init']['memory']=filtered
body=int(cap['init']['registers']['rcx'],0)
for variant in (('vector','scalar') if os.environ.get('TWIN_SCALAR_READY') == '1' else ('vector',)):
    full=json.loads((root/(variant+'-full.json')).read_text())
    records=full['streams'][0]['instructions']
    if variant=='scalar':
        calls=[i for i,r in enumerate(records) if r['op']=='call' and r['ops']==['nbReportTreeIncest']]
        assert len(calls)==1
        cut=calls[0]-2
        assert [r['op'] for r in records[cut:calls[0]]]==['mov','mov']
        label=records[cut]['label']
        assert any(r['op']=='ret' for r in records[:cut])
        assert any(r['op']=='call' and r['ops']==['nbGravity'] for r in records[:cut])
        records=copy.deepcopy(records[:cut])+[{'id':'cold_error_exit','op':'nop','ops':[],'label':label}]
        full['provenance']['region_cut']={'retained_records_identical':True,'exit_label':label,
            'reason':'S1-07 cold-error suffix only; normal return and all hot instructions retained'}
        full['provenance']['undeclared_callees']=[]
    else:
        assert not any(r['op']=='call' for r in records)
        full['provenance']['full_compiled_function_retained']=True
    for first in (0,1024,2048,4088):
        k=copy.deepcopy(full)
        k['init']=copy.deepcopy(cap['init'])
        k['init']['symbols']=full['init'].get('symbols',{})
        k['init']['memory'] += [b for b in full['init']['memory'] if 'file' not in b]
        k['init']['registers'].update({'rdi':'0x60000000','rcx':hex(body+first*128),'r8':8})
        k['streams']=[{'context':0,'instructions':records}]
        k['expected']={'memory':[{'addr':hex(0x60000000+l*32),'file':'capture/expected.bin',
             'offset':(first+l)*24,'length':24} for l in range(8)]}
        if variant=='vector': k['expected']['registers']={'0':{'rax':0}}
        k['scenario']=cap['scenario']; k['numerical_policy']=cap['numerical_policy']
        k['unit_of_work']={'count':8,'description':'eight contiguous bodies, first large force step'}
        k['provenance']['first_body']=first
        (root/('%s-%d.json'%(variant,first))).write_text(json.dumps(k,indent=2)+'\n')
print('Prepared compiled kernels for groups 0, 1024, 2048, 4088')
