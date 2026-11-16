"""S6-01 whole-workunit exactness, in addition to compare.py's numeric verdict."""
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests'))
from force_chunk_matrix import run, science
sys.path.insert(0,str(ROOT/'scripts'))
import compare
cases=[]
for case,threads in [('small',1),('small',12),('medium',1),('medium',12),('large',12)]:
    _,a=run((case,'vector-off',threads,'build/x86/milkyway_nbody.exe'))
    _,b=run((case,'vector-on',threads,'build/vector/x86-on/milkyway_nbody.exe'))
    assert compare.compare(a,b,compare.TOLERANCE)==0
    assert science(a)==science(b), 'exact scientific tokens differ: '+str(b)
    def saved(path):
        return b''.join(line for line in (path/'histogram.txt').read_bytes().splitlines(keepends=True) if not line.startswith(b'# Generated '))
    assert saved(a)==saved(b), 'saved histogram differs beyond generated timestamp'
    cases.append(case+'-'+str(threads))
    print('PASS %s-%d bit-identical likelihood, printed and saved histograms'%(case,threads),flush=True)
Path('twin/vector/exactness.json').write_text(json.dumps({'cases':cases,'all_exact':True},indent=2)+'\n')
