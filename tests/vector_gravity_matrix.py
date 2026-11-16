"""S6-01 whole-workunit exactness, in addition to compare.py's numeric verdict."""
from pathlib import Path
import json
import sys
import hashlib
import subprocess
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests'))
from force_chunk_matrix import run, science
sys.path.insert(0,str(ROOT/'scripts'))
import compare
# Build from the current source before recording evidence (including incremental reruns).
for variant, out in ((0, '../build/x86'), (1, '../build/vector/x86-on')):
    with open('build/s6-matrix-build-%d.log' % variant, 'w') as log:
        subprocess.run(['make', '-C', 'mk', '-j4', 'TARGET=x86',
                        'OUT='+out, 'VECTOR_GRAVITY='+str(variant), 'program'],
                       check=True, stdout=log, stderr=subprocess.STDOUT)
Path('twin/vector/exactness.json').unlink(missing_ok=True)
cases=[]
results=[]
for case,threads in [('small',1),('small',12),('medium',1),('medium',12),('large',12)]:
    _,a=run((case,'vector-off',threads,'build/x86/milkyway_nbody.exe'))
    _,b=run((case,'vector-on',threads,'build/vector/x86-on/milkyway_nbody.exe'))
    assert compare.compare(a,b,compare.TOLERANCE)==0
    assert science(a)==science(b), 'exact scientific tokens differ: '+str(b)
    def saved(path):
        return b''.join(line for line in (path/'histogram.txt').read_bytes().splitlines(keepends=True) if not line.startswith(b'# Generated '))
    assert saved(a)==saved(b), 'saved histogram differs beyond generated timestamp'
    cases.append(case+'-'+str(threads))
    results.append({'case': cases[-1], 'status': 'exact',
                    'reference': a.relative_to(ROOT).as_posix(),
                    'candidate': b.relative_to(ROOT).as_posix(),
                    'likelihood': science(a)[0],
                    'saved_histogram_sha256_without_generated_timestamp': hashlib.sha256(saved(a)).hexdigest()})
    print('PASS %s-%d bit-identical likelihood, printed and saved histograms'%(case,threads),flush=True)
Path('twin/vector/exactness.json').write_text(json.dumps({'cases':cases,'all_exact':True, 'results':results, 'binary_sha256': {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ('build/x86/milkyway_nbody.exe','build/vector/x86-on/milkyway_nbody.exe')}},indent=2)+'\n')
