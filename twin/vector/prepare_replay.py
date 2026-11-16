"""Copy and verify the unchanged S1-06 capture, then generate replay inputs."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
source = Path(sys.argv[1]) if len(sys.argv)>1 else Path('../S1-06/twin/multicore')
out = Path('twin/vector')
summary=json.loads((source/'capture-summary.json').read_text())
for name, info in summary['files'].items():
    p=source/'capture'/Path(name.replace(chr(92),chr(47))).name
    assert hashlib.sha256(p.read_bytes()).hexdigest()==info['sha256'], p
expected=(source/'capture/expected.bin').read_bytes()
assert len(expected)==4096*24
assert hashlib.sha256(expected).hexdigest()==summary['expected_xyz_sha256']
(out/'capture').mkdir(exist_ok=True)
for name in ('ctx','state','eps2','bodies','nodes','expected','layout-x86','layout-card'):
    shutil.copyfile(source/'capture'/(name+'.bin'),out/'capture'/(name+'.bin'))
assert (out/'capture/layout-x86.bin').read_bytes()[:176]==(out/'capture/layout-card.bin').read_bytes()[:176]
cap=json.loads((source/'capture.json').read_text())
(out/'capture.json').write_text(json.dumps(cap,indent=2)+'\n')
bodies=next(b for b in cap['init']['memory'] if b.get('file')=='capture/bodies.bin')
bodyaddr=int(bodies['addr'],0)
blocks=[]
cache={}
for b in cap['init']['memory']:
    if 'file' not in b: continue
    addr=int(b['addr'],0)
    if b['file']=='capture/nodes.bin' and bodyaddr<=addr<bodyaddr+2560000: continue
    if b['file'] not in cache: cache[b['file']]=(out/b['file']).read_bytes()
    data=cache[b['file']]
    offset=b.get('offset',0)
    data=data[offset:offset+b.get('length',len(data))]
    blocks.append((addr,1 if b['file']=='capture/nodes.bin' else 0,data))
blocks.sort()
rows=[]
with (out/'replay.bin').open('wb') as f:
    for addr,kind,data in blocks:
        rows.append('{%dULL,%d,%d,%d,0}'%(addr,len(data),f.tell(),kind))
        f.write(data)
(out/'replay_blocks.h').write_text('struct Block { uintptr_t addr; size_t size; long offset; int kind; unsigned char *data; };\nstatic struct Block blocks[]={\n'+',\n'.join(rows)+'\n};\n#define CTX_ADDR '+cap['init']['registers']['rsi']+'ULL\n#define STATE_ADDR '+cap['init']['registers']['rdx']+'ULL\n')
(out/'capture-provenance.json').write_text(json.dumps(summary,indent=2)+'\n')
print('Verified S1-06 capture and 98,304 independent expected XYZ bytes; %d relocated blocks'%len(blocks))
