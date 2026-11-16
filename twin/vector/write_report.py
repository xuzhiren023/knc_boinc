"""S6-03 evidence from final binaries and raw twin results; no partial timings."""
import collections
import hashlib
import json
import os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
root = ROOT/'twin/vector'
def load(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
k = load(root/'vector-full.json')
r = k['streams'][0]['instructions']
ops = collections.Counter(x['op'] for x in r)
x87 = {op:n for op,n in ops.items() if op.startswith(('fadd','fsub','fmul','fdiv','fsqrt'))}
x87_remaining = {op:n for op,n in ops.items() if op.startswith('f')}
cap = load(root/'capabilities.json')
report = {'status': 'host/codegen and twin vector replay checked; card A/B pending',
    'macro_default': 0, 'capabilities': cap,
    'codegen': {
        'zmm_arithmetic': all(ops[op] for op in ('vaddpd','vsubpd','vmulpd')),
        'masked_zmm_arithmetic': all(ops[op] for op in ('vpandq','vpxorq')),
        'mask_implementation': 'bit selection preserves inactive accumulator bits',
        'no_x87_arithmetic': not x87, 'x87_arithmetic': x87,
        'remaining_x87': x87_remaining,
        'remaining_x87_reason': 'scalar guarded packing and unpacking use fld/fst/fxch; fcompl/fnstsw implement cell-opening comparison; no x87 add/sub/mul/div/sqrt',
        'refinement_instructions': {op:n for op,n in ops.items() if op.startswith(('vfm','vfnm','vrcp','vrsqrt'))},
        'source_contraction': 'off; FMAs occur only in correctly rounded compiler div/sqrt expansions (GCC-KNC S10-09)',
        'instructions': len(r), 'opcode_counts': dict(ops),
        'full_compiled_function_retained': not any(x['op']=='call' for x in r),
        'compiler_flags': '-O2 -g -fopenmp -fno-strict-aliasing -ffp-contract=off -fno-math-errno -march=knc -std=gnu99',
        'optimized_report': 'twin/vector/vectorizer.txt',
        'disassembly': 'twin/vector/nbGravity8.disassembly.txt',
        'literal_full_vector_requirement_met': not x87},
    'exactness': load(root/'exactness.json'), 'groups': []}
for name, digest in report['exactness']['binary_sha256'].items():
    assert sha(ROOT/name) == digest, 'matrix was not run with final binary: '+name
report['exactness'].update({
    'acceleration_bytes': (root/'actual.bin').stat().st_size,
    'accelerations_exact': (root/'actual.bin').read_bytes() == (root/'actual-off.bin').read_bytes() == (root/'capture/expected.bin').read_bytes(),
    'acceleration_sha256': sha(root/'actual.bin'), 'range_audit': load(root/'range.json')})
util = load(root/'lane-utilization.json')
scalar_ready = os.environ.get('TWIN_SCALAR_READY') == '1'
for first in (0,1024,2048,4088):
    group = {'first_body':first, 'comparison': 'waiting for S14-37' if not scalar_ready else 'same-profile baseline',
             'scalar_functional': 'not rerun: S14-37 is not installed' if not scalar_ready else None}
    for variant in (('vector','scalar') if scalar_ready else ('vector',)):
        for mode in ('functional','simulate'):
            result = load(root/f'{variant}-{first}-{mode}/result.json')
            group[variant+'_'+mode] = result['status']
            evidence = {key:result.get(key) for key in
                ('engine_version','status','message','functional_check','assumptions','unsupported',
                 'limiting_constraints','calibration_status','result_class','parameters_used')}
            group[variant+'_'+mode+'_evidence'] = evidence
            if mode == 'simulate' and result.get('prediction'):
                pred = result['prediction']
                evidence['result_class'] = pred.get('result_class')
                evidence['functional_exactness'] = pred.get('functional_exactness')
                evidence['approximate_instructions'] = pred.get('approximate_instructions')
                evidence['profile'] = {x:result['profile'].get(x) for x in ('id','hash','version','synthetic')}
                # The skill permits cycle predictions only for status-ok runs.
                if result['status']=='ok' and group[variant+'_functional']=='ok':
                    group[variant+'_cycles_per_body'] = pred['predicted_cycles_per_unit']
                    group[variant+'_result_class'] = pred['result_class']
    group.update(util[str(first)])
    report['groups'].append(group)
report['timing'] = {'classification': 'unvalidated_scenario_estimate; gravity is not a validated shape',
    'policy': 'Only status-ok matching functional and simulate runs supply cycles. Approximate seeds cannot prove native bytes.',
    'constraints': ['guarded scalar pointer packing', 'stack staging', 'longest-walk group divergence'],
    'scalar_baseline': cap['scalar_baseline']}
current = load(root/'vector-current.json')
assert k['streams'] == current['streams'] and k['init']['memory'] == current['init']['memory']
for first in (0,1024,2048,4088):
    executed = load(root/f'vector-{first}.json')
    assert executed['streams'][0]['instructions'] == r
report['codegen']['final_extraction_matches_executed_kernel'] = True
report['artifacts'] = {p.relative_to(ROOT).as_posix():sha(p) for p in [
    ROOT/'build/x86/milkyway_nbody.exe', ROOT/'build/vector/x86-on/milkyway_nbody.exe',
    ROOT/'build/vector/card-off/milkyway_nbody.mic', ROOT/'build/vector/card-on/milkyway_nbody.mic',
    ROOT/'patches/nbody-vector-gravity.patch']}
(root/'evidence.json').write_text(json.dumps(report,indent=2)+'\n')
print('S6-03: x87 arithmetic',x87,'; host matrix exact:',report['exactness']['all_exact'],
      '; 98,304 acceleration bytes exact:',report['exactness']['accelerations_exact'])
for g in report['groups']:
    print('group',g['first_body'],'functional',g['vector_functional'],'simulate',g['vector_simulate'],
          'cycles/body',g.get('vector_cycles_per_body','withheld'), 'lane utilization',g['lane_utilization'])
