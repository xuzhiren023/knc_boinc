"""Render S1-05 evidence from unchanged knc-twin 0.4.0 result envelopes."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def read(path):
    return json.loads((ROOT/path).read_text())

def render():
    text = '''# S1-05: knc-twin 0.4.0 rerun

The unchanged 0.4.0 engine passes the four-instruction `fildl` repro (exact
+0.0, bits `0000000000000000`) and all 16 `log_rn` cases. The earlier S1-04
integer-width mismatch is resolved. The full compiled `log_rn` and `p_accu`
bodies, ELF constants and captured ABI input are retained. Expected bits come
from the S1-04 independent Cygwin x86 probe, never from the twin.
`twin/log-diagnosis.json`, `log-memory.md`, and the width diagnostic describe
the historical S1-04 failure; current cases are in `twin/log-rerun.json` and
`twin/log-cases/*/result.json`.

Gravity validate, functional, simulate and bounds all return `ok`. Its
captured acceleration matches the independent host output. No card comparison:
the card run has not happened. These are model results, not measured card timings.

## Region boundary and reference evidence

The gravity region was cut at the error branch because S14-20 has not landed:
the adapter refuses the indirect fprintf PLT path even when it never executes.
`from_binary.py` first extracts the complete built `nbGravity` without an
invented callee stub. `twin/cut_gravity.py` keeps the first 202 instruction
records exactly, with their operands, encodings, addresses, dependencies,
output stores, stack epilogue and normal return unchanged. At `.A_4050b2`,
before the cold call setup for `nbReportTreeIncest`, it places an exit label.
The branch at `0x405044` still targets that label. The error block and later
unreachable padding are excluded. Neither application source nor shared twin
code is changed. Full-function conversion evidence remains in `conversion.json`;
`gravity-region.json` describes the narrower executable region.

The functional trace executes 3,040 instructions, reaches the normal return,
and never reaches the exit sentinel. At `0x405044`, `je .A_4050b2` is **not
taken**. `twin/gravity-execution.json` retains this evidence. A fresh host
reference (`bash scripts/run_x86.sh small 1`, seed 670828913, 64 bodies) exits
zero; stdout and stderr have zero `tree-incest` diagnostics. The captured
warning gates are `quietErrors=0` and `treeIncest=0`, so the first error would
print. `twin/gravity-reference.json` records output byte counts and hashes,
command, and histogram hash. This establishes absence only for this measured
input, not arbitrary gravity inputs.

## Per-call model cycles

Both simulations use one context, `card-7120-measured`, cold `line_tracking`
memory, predicted branches and x87 control word `0x027f` (53-bit precision).
Each unit is one captured call; the log timing is for the captured 1.0 input,
not an average of the 16 cases.

| Region | simulate cycles/call | result_class | bounds cycles/call | result_class |
| --- | ---: | --- | ---: | --- |
| log_rn | 2,778 | unvalidated_scenario_estimate | 2,597 | conditional_bound |
| nbGravity, cold error region excluded | 33,622 | unvalidated_scenario_estimate | 43,656 | conditional_bound |

The gravity lower bound **exceeds** its simulation prediction. Both commands
return `ok`; these are the exact engine outputs. This is an unresolved
model inconsistency, so do not treat the pair as a consistent timing interval
or use it to choose close variants. No model correction is attempted here.
Both bounds identify `dependency_critical_path` as the binding term. Simulation
constraints and all returned assumptions follow below. Neither kernel declares
a validated `provenance.shape`; no calibrated forecast is claimed.

## Functional cases

| Case | Input bits | Independent expected log bits | 0.4.0 status |
| --- | --- | --- | --- |
'''
    for case in read('twin/log-rerun.json'):
        text += '| {case} | `{input_bits}` | `{expected_bits}` | {status} |\n'.format(**case)
    text += '\n## Returned fields\n\nMissing fields are written as `"<absent>"`, distinct from null.\n'
    calibrations = []
    paths = ['validate','functional','simulate','bounds','hot/validate','hot/functional',
             'hot/simulate','hot/bounds','fildl-repro']
    for path in paths:
        result = read('twin/'+path+'/result.json')
        text += '\n### '+path+'\n\n'
        for key in ('status','functional_check','assumptions','unsupported','limiting_constraints'):
            text += '- `'+key+'`: `'+json.dumps(result.get(key,'<absent>'), sort_keys=True)+'`\n'
        # Preserve both the top-level location and the prediction's actual class.
        text += '- top-level `result_class`: `'+json.dumps(result.get('result_class','<absent>'),sort_keys=True)+'`\n'
        prediction = result.get('prediction') or {}
        if 'result_class' in prediction:
            text += '- `prediction.result_class`: `'+json.dumps(prediction['result_class'], sort_keys=True)+'`\n'
        used = {key: value for key, value in result.get('parameters_used', {}).items()
                if value.get('status') in ('assumed', 'derived')}
        text += '- assumed/derived `parameters_used`: `'+json.dumps(used,sort_keys=True)+'`\n'
        calibration = result.get('calibration_status','<absent>')
        if calibration not in calibrations:
            calibrations.append(calibration)
        text += '- `calibration_status`: shared entry '+str(calibrations.index(calibration)+1)+' below.\n'
    text += '\n### Shared calibration_status values\n\n'
    for i, value in enumerate(calibrations,1):
        text += str(i)+'. `'+json.dumps(value, sort_keys=True)+'`\n\n'
    text += '''## Reproduce

From Git Bash at the worktree root, with the existing pinned upstream sources:

```bash
mkdir -p build/tmp
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
export PATH="/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin:$PATH"
export PYTHONDONTWRITEBYTECODE=1
make -C mk -j4 card
make -C mk -j4 x86
bash scripts/run_x86.sh small 1
python C:/Users/xuzhi/.claude/skills/knc-twin/scripts/knc_twin.py capabilities --out twin/capabilities --force
python C:/Users/xuzhi/.claude/skills/knc-twin/scripts/knc_twin.py functional twin/fildl-repro.json --trace --out twin/fildl-repro --force
bash twin/run_hot.sh
bash twin/run.sh
python twin/write_report.py
python tests/test_twin_040.py
python tests/test_twin.py
```

The committed capture files and independent S1-04 expected bits are reused.
Full disassemblies, extracted kernels, final memory snapshots, gravity trace
and issue logs remain ignored by `twin/.gitignore`. Compact results and the
16 functional traces remain reviewable evidence. The card executable and
runtimes are staged under `dist/card/`; `scripts/card-check.sh` prints the
lead's run instructions. No card access, downloads, installs or git writes
were performed.
'''
    (ROOT/'docs/twin-check.md').write_text(text)

if __name__ == '__main__':
    render()
