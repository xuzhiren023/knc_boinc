"""S14-20 workaround: end before the cold nbReportTreeIncest call block.

All retained binary instruction records, including branches and the normal
return/output stores, are identical to the full adapter output.
"""
import copy
import json
import os
from pathlib import Path
import sys
sys.dont_write_bytecode = True
home = Path(os.environ.get('TWIN_HOME', 'C:/Users/xuzhi/.claude/skills/knc-twin'))
sys.path.insert(0, str(home/'scripts'))
from from_gcc_s import classify_records, summarize
from knc_model.profile import load_profile

kernel = json.loads(Path('twin/gravity-full.json').read_text())
records = kernel['streams'][0]['instructions']
calls = [i for i, row in enumerate(records)
         if row['op'] == 'call' and row['ops'] == ['nbReportTreeIncest']]
assert len(calls) == 1
cut = calls[0] - 2
assert [row['op'] for row in records[cut:calls[0]]] == ['mov', 'mov']
label = records[cut]['label']
kept = copy.deepcopy(records[:cut])
assert any(row['op'] == 'ret' for row in kept), 'normal epilogue must remain'
assert any(row['op'] == 'je' and row['ops'] == [label] for row in kept)
assert not any(row['op'] == 'call' for row in kept)
# The original branch target becomes the region exit. No hot-path instruction
# or operand is rewritten. This sentinel must never execute on the capture.
kept.append({'id': 'cold_error_exit', 'op': 'nop', 'ops': [], 'label': label})
kernel['streams'][0]['instructions'] = kept
kernel.pop('memory_default', None)
p = kernel['provenance']
p['undeclared_callees'] = []
p['coverage'] = summarize(classify_records(kept, load_profile('card-7120-measured')))
p['region_cut'] = {'exit_label': label, 'first_excluded_instruction': records[cut],
                   'removed_instructions': len(records)-cut,
                   'reason': 'S14-20 pending: cold fprintf PLT path refused even when unexecuted',
                   'retained_records_identical': kept[:-1] == records[:cut]}
kernel['description'] += '; region ends before cold error branch block; normal return retained'
Path('twin/kernel.json').write_text(json.dumps(kernel, indent=2)+'\n')
Path('twin/gravity-region.json').write_text(json.dumps(p['region_cut'], indent=2)+'\n')
print('Gravity region exit: %s; %d unchanged binary instructions; cold call excluded' % (label, cut))
