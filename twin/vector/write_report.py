"""Compact truthful S6-01 evidence; never promote mismatching timings."""
import collections
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests'))
from force_chunk_matrix import science
sys.path.insert(0,str(ROOT/'scripts'))
import compare
root=ROOT/'twin/vector'
def load(path): return json.loads(path.read_text())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
k=load(root/'vector-full.json')
r=k['streams'][0]['instructions'];ops=collections.Counter(x['op'] for x in r)
x87={op:n for op,n in ops.items() if op.startswith(('fadd','fsub','fmul','fdiv','fsqrt'))}
forbidden={op:n for op,n in ops.items() if op.startswith(('vfm','vfnm','vrcp','vrsqrt'))}
report={'status':'incomplete: stopped at exactness/codegen gates',
    'macro_default':0,'codegen':{
        'zmm_arithmetic':any(x['op'] in ('vaddpd','vsubpd','vmulpd') for x in r),
        'masked_zmm_arithmetic':all(ops[op] for op in ('vpandq','vpxorq')),
        'mask_implementation':'bit selection of untouched accumulator bits, not k-register predication',
        'no_x87_arithmetic':not x87,'x87_arithmetic':x87,'forbidden_instructions_in_final_kernel':forbidden,
        'instructions':len(r),'opcode_counts':dict(ops),
        'full_compiled_function_retained':not any(x['op']=='call' for x in r),
        'compiler_flags':'-O2 -g -fopenmp -fno-strict-aliasing -ffp-contract=off -fno-math-errno -march=knc -std=gnu99',
        'optimized_report':'twin/vector/vectorizer.txt','disassembly':'twin/vector/nbGravity8.disassembly.txt',
        'literal_full_vector_requirement_met':False},'exactness':{},'groups':[]}
# The early matrix and final refresh share identical final scientific behavior;
# use the final refresh directories except for the long 1-thread medium case.
def sha_normalized(data): return hashlib.sha256(data).hexdigest()
rows=[]
for case,threads in [('small',1),('small',12),('medium',1),('medium',12),('large',12)]:
    final=ROOT/'runs/force-chunk'/('%s-chunkvector-final-on-t%d'%(case,threads))
    label='vector-final' if (case,threads)!=('medium',1) and (final/'exit.txt').exists() else 'vector'
    a=ROOT/'runs/force-chunk'/('%s-chunk%s-off-t%d'%(case,label,threads))
    b=ROOT/'runs/force-chunk'/('%s-chunk%s-on-t%d'%(case,label,threads))
    if not (a/'exit.txt').exists() or not (b/'exit.txt').exists():
        rows.append({'case':case+'-'+str(threads),'status':'not completed'})
        continue
    assert (a/'exit.txt').read_text().strip()==(b/'exit.txt').read_text().strip()=='0'
    print('%s-%d macro off vs on:'%(case,threads))
    code=compare.compare(a,b,compare.TOLERANCE)
    def saved(p):
        return b''.join(line for line in (p/'histogram.txt').read_bytes().splitlines(keepends=True)
                        if not line.startswith(b'# Generated '))
    exact=science(a)==science(b) and saved(a)==saved(b) and code==0
    rows.append({'case':case+'-'+str(threads),'status':'exact' if exact else 'mismatch',
        'likelihood':science(a)[0], 'saved_histogram_sha256_without_generated_timestamp':sha_normalized(saved(a)),
        'reference':a.relative_to(ROOT).as_posix(),'candidate':b.relative_to(ROOT).as_posix(),
        'histogram_difference_policy':'only # Generated timestamp omitted; every other byte compared'})
report['exactness']={'cases':[x['case'] for x in rows], 'results':rows,
    'all_exact':all(x['status']=='exact' for x in rows),
    'acceleration_bytes':(root/'actual.bin').stat().st_size,
    'accelerations_exact':(root/'actual.bin').read_bytes()==(root/'capture/expected.bin').read_bytes(),
    'acceleration_sha256':sha(root/'actual.bin'),'range_audit':load(root/'range.json')}
util=load(root/'lane-utilization.json') if (root/'lane-utilization.json').exists() else {}
for first in (0,1024):
    group={'first_body':first,'comparison':'waiting for S14-37'}
    for variant in ('vector','scalar'):
        for mode in ('functional','simulate'):
            path=root/('%s-%d-%s/result.json'%(variant,first,mode))
            if not path.exists():
                group[variant+'_'+mode]='not completed';continue
            result=load(path)
            group[variant+'_'+mode]=result['status']
            group[variant+'_'+mode+'_evidence']={key:result.get(key) for key in
                ('engine_version','status','message','functional_check','assumptions','unsupported',
                 'limiting_constraints','calibration_status','result_class','parameters_used')}
            if mode=='simulate' and result.get('prediction'):
                group[variant+'_'+mode+'_evidence']['result_class']=result['prediction'].get('result_class')
                group[variant+'_'+mode+'_evidence']['parameters_used']=result.get('parameters_used')
                group[variant+'_'+mode+'_evidence']['profile']={x:result['profile'].get(x) for x in ('id','hash','version','synthetic')}
            # A non-ok status is evidence of a blocker, never a cycle estimate.
            if mode=='simulate' and result['status']=='ok' and group.get(variant+'_functional')=='ok':
                pred=result['prediction']
                group[variant+'_cycles_per_body']=pred['predicted_cycles_per_unit']
                group[variant+'_result_class']=pred['result_class']
    if str(first) in util:
        group.update(util[str(first)])
    report['groups'].append(group)
report['timing']={'cycles_per_body':'see only status-ok per-group entries','result_class':'unvalidated_scenario_estimate for passing group 1024 only',
    'reason':'Only status-ok matching per-group runs may supply timing. Mismatch/budget partials are not predictions.',
    'classification_if_a_future_run_passes':'unvalidated_scenario_estimate; gravity shape is not validated',
    'observed_codegen_constraints':['scalar x87 sqrt and division','scalar quadrupoles and pointer packing',
        'stack staging and longest-walk group divergence'],
    'twin_limiting_constraints':'copied per run above; no timing constraints were emitted for these failed runs'}
current=load(root/'vector-current.json') if (root/'vector-current.json').exists() else k
assert k['streams']==current['streams'] and k['init']['memory']==current['init']['memory']
report['codegen']['final_extraction_matches_executed_kernel']=True
report['artifacts']={str(p.relative_to(ROOT)).replace(chr(92),'/'):sha(p) for p in
    [ROOT/'build/x86/milkyway_nbody.exe',ROOT/'build/vector/x86-on/milkyway_nbody.exe',
     ROOT/'build/vector/card-off/milkyway_nbody.mic',ROOT/'build/vector/card-on/milkyway_nbody.mic',
     ROOT/'build/gravity_chunk.mic',ROOT/'patches/nbody-vector-gravity.patch']}
(root/'evidence.json').write_text(json.dumps(report,indent=2)+'\n')
print('S6-01: exact host cases %d/5; acceleration bytes %d exact=%s; twin/codegen gates remain failed'%(
    sum(x['status']=='exact' for x in rows),report['exactness']['acceleration_bytes'],report['exactness']['accelerations_exact']))
