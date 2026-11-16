"""Regenerate S1-06 inputs, isolate the six bodies, and audit x87 arithmetic.

The audit records every arithmetic operation on the unchanged twin path, then
replays those operands with native x87 instructions at PC=53. No model edits.
"""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
sys.dont_write_bytecode = True
home = Path(os.environ.get('TWIN_HOME', 'C:/Users/xuzhi/.claude/skills/knc-twin'))
sys.path.insert(0, str(home/'scripts'))
from knc_model.kernel import load_kernel
from knc_model.functional import Interpreter
from knc_model import fp
ROOT = Path('twin/multicore')
BODIES = [1024, 1408, 1664, 3072, 3200, 3584]

def f64(v):
    bits = fp.convert(v, fp.F80, fp.F64)[0]
    assert fp.convert(bits, fp.F64, fp.F80)[0] == v, 'oracle operand lost precision'
    return bits

class Audit(Interpreter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.operations = []
    def record(self, cx, op, a, b, r):
        insn = self.kernel.streams[0].insns[cx.pc]
        self.operations.append({'id': insn.id, 'op': op, 'a': '%016x'%f64(a),
                                'b': '%016x'%f64(b), 'twin': '%016x'%f64(r),
                                'instruction': insn.op, 'ordinal': len(self.operations)})
    def _x87_binop(self, op, a, b, cx):
        r = super()._x87_binop(op, a, b, cx)
        self.record(cx, op, a, b, r)
        return r
    def h_x87(self, cx, insn, ev, trace_mem, stream):
        if insn.op == 'fsqrt':
            a = cx.fget(0, insn)
            super().h_x87(cx, insn, ev, trace_mem, stream)
            self.record(cx, 'sqrt', a, a, cx.fget(0, insn))
        else:
            super().h_x87(cx, insn, ev, trace_mem, stream)

def main():
    base = json.loads((ROOT/'unit.json').read_text())
    runs = []
    first = None
    for body in BODIES:
        slot = body//128
        k = copy.deepcopy(base)
        k['name'] = 'large-body-%d-core-isolation'%body
        k['streams'] = [k['streams'][slot]]
        k['streams'][0]['core'] = k['streams'][0]['context'] = 0
        k['expected']['memory'] = [k['expected']['memory'][slot]]
        k['unit_of_work'] = {'count':1, 'description':'one isolated large body'}
        path = ROOT/('body-%d.json'%body)
        path.write_text(json.dumps(k, indent=2)+'\n')
        out = ROOT/('body-%d'%body)
        cmd = [sys.executable,str(home/'scripts/knc_twin.py'),'simulate',str(path),
               '--scale','core','--profile','card-7120-measured','--max-seconds','1740',
               '--no-issue-log','--out',str(out),'--force']
        print('$ '+' '.join(cmd), flush=True)
        run = subprocess.run(cmd)
        result = json.loads((out/'result.json').read_text())
        runs.append({'body':body, 'status':result['status'], 'exit':run.returncode,
                     'functional_check':result.get('functional_check'),
                     'result':str(out/'result.json'), 'scale':result['scale'],
                     'contexts':result['input']['kernel']['contexts'], 'engine_version':result['engine_version']})
        audit = Audit(load_kernel(str(path)))
        audit.run()
        operands = ''.join('{op} {a} {b}\n'.format(**r) for r in audit.operations)
        native = subprocess.run([str(Path('build/x87_oracle.exe').resolve())],input=operands,text=True,
                                stdout=subprocess.PIPE,check=True).stdout.splitlines()
        assert len(native) == len(audit.operations)
        differences = [dict(r,native=n) for r,n in zip(audit.operations,native) if r['twin'] != n]
        runs[-1]['arithmetic_operations_checked'] = len(native)
        runs[-1]['operation_differences'] = differences
        print('body %d: %d native operations, %d differing; first %s' %
              (body,len(native),len(differences), differences[:1]), flush=True)
        if first is None and differences:
            first = differences[0]
    evidence = {'body_indices':BODIES,'core_runs':runs, 'odd_one_out':'twin',
                'first_operation':first, 'oracle_control_word':'0x027f',
                'oracle':'native x87 replay of each arithmetic operation on the unchanged twin path'}
    assert first, 'no arithmetic difference found; investigate traversal/load semantics'
    (ROOT/'isolation.json').write_text(json.dumps(evidence,indent=2)+'\n')
    repro = {'schema':'knc-twin.kernel/1','entry':'function',
             'name':'x87 PC53 double rounding: '+first['op'],
             'numerical_policy':base['numerical_policy'],
             'init':{'memory':[{'addr':'0x1000','u64':['0x'+first['a'],'0x'+first['b']]}]},
             'expected':{'memory':[{'addr':'0x2000','u64':['0x'+first['native']]}]},
             'streams':[{'context':0,'instructions':[
                 {'id':'load','op':'fldl','ops':[{'abs':True,'disp':4096}]},
                 {'id':'operation','op':{'add':'faddl','sub':'fsubl','mul':'fmull','div':'fdivl'}[first['op']], 'ops':[{'abs':True,'disp':4104}]},
                 {'id':'store','op':'fstpl','ops':[{'abs':True,'disp':8192}]},
                 {'id':'return','op':'ret','ops':[]}]}]}
    Path('twin/x87-rounding-repro.json').write_text(json.dumps(repro,indent=2)+'\n')
if __name__ == '__main__':
    main()
