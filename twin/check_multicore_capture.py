"""Check first-force snapshot integrity and target layout without twin timing."""
import hashlib
import json
from pathlib import Path
root = Path('twin/multicore')
capture = json.loads((root/'capture.json').read_text())
assert Path('build/s1-06-capture-exit.txt').read_text().strip() == '0'
for stream in ('stdout', 'stderr'):
    assert b'tree-incest' not in Path('build/s1-06-capture-'+stream+'.txt').read_bytes().lower()
a = (root/'capture/layout-x86.bin').read_bytes()
b = (root/'capture/layout-card.bin').read_bytes()
assert a[:176] == b[:176] and not any(a[176:]) and not any(b[176:])
assert capture['capture_layout']['bodies'] == 20000
assert capture['capture_layout']['chunk_bodies'] == 128
assert (root/'capture/expected.bin').stat().st_size == 4096*24
files = {}
for block in capture['init']['memory']:
    if 'file' not in block:
        continue
    p = root/block['file']
    if str(p) not in files:
        data = p.read_bytes()
        files[str(p)] = {'bytes':len(data), 'sha256':hashlib.sha256(data).hexdigest()}
    assert block.get('offset', 0)+block.get('length', p.stat().st_size) <= p.stat().st_size
result = {'exit':0, 'tree_incest_diagnostics':0, 'layout_matches':True,
          'capture_layout':capture['capture_layout'], 'files':files,
          'expected_xyz_sha256':hashlib.sha256((root/'capture/expected.bin').read_bytes()).hexdigest(),
          'app_card_sha256':hashlib.sha256(Path('build/card/milkyway_nbody.mic').read_bytes()).hexdigest(),
          'expected_xyz_bodies':4096, 'force_step':0, 'seed':670828913,
          'command':'OMP_NUM_THREADS=1 OMP_DYNAMIC=FALSE build/capture.exe -f workunits/large/params.lua -h workunits/large/input.hist --seed 670828913 --nthreads 1 --print-histogram --ignore-checkpoint --checkpoint-interval=-1 -z build/s1-06-capture.hist -c build/s1-06-capture.checkpoint 20000'}
(root/'capture-summary.json').write_text(json.dumps(result,indent=2)+'\n')
print('Large capture: 20000 bodies; first-force tree; 4096 independent XYZ results; target layouts match; no tree-incest diagnostics')
