"""Rerun the 16 S1-04 inputs against their independent x86 expected bits."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys

home = Path(os.environ.get('TWIN_HOME', 'C:/Users/xuzhi/.claude/skills/knc-twin'))
source = json.loads(Path('twin/log-kernel.json').read_text())
cases = json.loads(Path('twin/log-diagnosis.json').read_text())['cases']
assert len(cases) == 16
out = Path('twin/log-cases')
summary = []
for case in cases:
    kernel = copy.deepcopy(source)
    kernel['init']['registers']['zmm0'] = {'u64': ['0x'+case['input_bits']] + [0]*7}
    kernel['expected']['registers']['0']['zmm0'] = {'u64': ['0x'+case['expected_bits']]}
    for block in kernel['init']['memory']:
        if 'file' in block:
            block['file'] = '../'+block['file']
    path = out/(case['case']+'.json')
    path.write_text(json.dumps(kernel)+'\n')
    command = [sys.executable, str(home/'scripts/knc_twin.py'), 'functional', str(path),
               '--trace', '--out', str(out/case['case']), '--force']
    run = subprocess.run(command, capture_output=True, text=True)
    (out/case['case']/'command.log').write_text(run.stdout+run.stderr)
    result = json.loads((out/case['case']/'result.json').read_text())
    row = {key: case[key] for key in ('case', 'input_bits', 'expected_bits')}
    row.update(status=result['status'], functional_check=result.get('functional_check'))
    summary.append(row)
    print('%s input=%s expected=%s: %s' %
          (case['case'], case['input_bits'], case['expected_bits'], result['status']), flush=True)
    if run.returncode or result['status'] != 'ok':
        Path('twin/log-rerun.json').write_text(json.dumps(summary, indent=2)+'\n')
        sys.exit('STOP: differing case; inspect retained trace before further work')
Path('twin/log-rerun.json').write_text(json.dumps(summary, indent=2)+'\n')
print('log_rn: all 16 cases match independent x86 expected bits')
