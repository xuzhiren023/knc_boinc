"""Use the S1-06 repacked capture with a compiled caller and real nbGravity."""
import argparse
import copy
import json
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('--bodies',type=int,default=128)
a=p.parse_args()
assert 1 <= a.bodies <= 128
root=Path('twin/multicore')
base=json.loads((root/'unit.json').read_text())
full=json.loads((root/'chunk-full.json').read_text())
records=full['streams'][0]['instructions']
calls=[i for i,r in enumerate(records) if r['op']=='call' and r['ops']==['nbReportTreeIncest']]
assert len(calls)==1
cut=calls[0]-2
assert [r['op'] for r in records[cut:calls[0]]]==['mov','mov']
assert any(r['op']=='call' and r['ops']==['nbGravity'] for r in records[:cut])
assert any(r['op']=='ret' for r in records[:cut])
label=records[cut]['label']
kept=copy.deepcopy(records[:cut])+[{'id':'cold_error_exit','op':'nop','ops':[],'label':label}]
# The nbGravity instructions come from exactly the app object; no hot edits.
app_kernel=json.loads(Path('twin/kernel.json').read_text())
app=app_kernel['streams'][0]['instructions'][:-1]
def strip_adapter_namespace(value):
    if isinstance(value, str):
        return value.replace('nbGravity_a', 'a').replace('nbGravity.A_', '.A_')
    if isinstance(value, list):
        return [strip_adapter_namespace(x) for x in value]
    if isinstance(value, dict):
        return {k:strip_adapter_namespace(v) for k,v in value.items()}
    return value
def constant_bytes(kernel, address, width):
    for block in kernel['init']['memory']:
        if 'hex' in block:
            start=int(str(block['addr']),0)
            data=bytes.fromhex(block['hex'])
            if start <= address and address+width <= start+len(data):
                return data[address-start:address-start+width]
    raise AssertionError('constant missing from adapter memory')
normalized=strip_adapter_namespace(kept[-len(app)-1:-1])
relocations=[]
for old,new in zip(app,normalized):
    for x,y in zip(old['ops'],new['ops']):
        if isinstance(x,dict) and isinstance(y,dict) and x.get('abs') and x != y:
            width=4 if old['op'].endswith('s') else 8
            assert constant_bytes(app_kernel,x['disp'],width)==constant_bytes(full,y['disp'],width)
            relocations.append({'id':old['id'],'old':x['disp'],'new':y['disp'],'bytes':width})
            y['disp']=x['disp']  # comparison copy only; kept records stay unchanged
assert normalized==app, 'linked callee changed beyond adapter namespace and verified constant relocation'
(root/'chunk-build-evidence.json').write_text(json.dumps({'constant_relocations':relocations,
    'callee_identical_except_linker_relocations':True,'retained_adapter_records_unchanged':True},indent=2)+chr(10))
body=int(base['init']['registers']['rcx'],16)
for name,cores in [('chunk-baseline',1),('chunk-unit',8),('chunk-ring',8)]:
    k=copy.deepcopy(full)
    k['streams']=[]
    k['expected']={'memory':[]}
    k['init']=copy.deepcopy(base['init'])
    k['init']['symbols']=full['init'].get('symbols',{})
    k['init']['memory']=[b for b in k['init']['memory'] if 'file' in b]+[b for b in full['init']['memory'] if 'file' not in b]
    k['scenario']=base['scenario']
    k['numerical_policy']=base['numerical_policy']
    for slot in range(cores*4):
        output=0x70000000+slot*8192
        k['streams'].append({'context':slot%4,'core':slot//4,
            'init':{'registers':{'rdi':output,'rcx':body+slot*128*128,'r8':a.bodies}},
            'instructions':kept})
        # mwvector has a fourth, unspecified lane. Compare XYZ only.
        for i in range(a.bodies):
            k['expected']['memory'].append({'addr':hex(output+i*32),
                'file':'capture/expected.bin','offset':(slot*128+i)*24,'length':24})
    # Count is aggregate work, as specified by the twin schema. compare's strict
    # equal-count policy may still reject 4 versus 32 equal-length streams.
    k['unit_of_work']={'count':cores*4*a.bodies,
        'description':'contiguous bodies in distinct 128-body chunks; equal bodies per context'}
    k['provenance']['region_cut']={'exit_label':label,'retained_records_identical':True,
        'reason':'same S1-05 cold-error cut, after compiled caller plus nbGravity'}
    k['provenance']['s1_07']={'bodies_per_context':a.bodies,'chunk_bodies':128,
        'linked_app_object':'build/card/nbody/src/nbody_grav.c.o',
        'symbol_visibility_only':True,'callee_matches_app_records':True}
    (root/(name+'.json')).write_text(json.dumps(k,indent=2)+'\n')
print('Compiled driver: %d bodies/context; 4/32/32 distinct chunks; unchanged callee records'%a.bodies)
