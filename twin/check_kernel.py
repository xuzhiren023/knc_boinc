"""Audit unsupported instructions and capture completeness before tool validation."""
import json
from pathlib import Path

root = Path(__file__).resolve().parent
kernel_path = root / 'kernel.json'
kernel = json.loads(kernel_path.read_text())
capabilities = json.loads((root / 'capabilities/capabilities.json').read_text())
isa = {row['mnemonic']: row['functional'] for row in capabilities['instructions']}
blockers = []
for stream in kernel['streams']:
    for row in stream['instructions']:
        if not isa.get({'fildll': 'fildq'}.get(row['op'], row['op']), False):
            blockers.append('unsupported or timing-only: ' + row['op'])
provenance = kernel['provenance']
for key in ('unresolved_symbols', 'undeclared_callees'):
    if provenance.get(key):
        blockers.append(key + ': ' + repr(provenance[key]))
if provenance.get('coverage', {}).get('unsupported'):
    blockers.append('adapter reported unsupported instructions')
for section in ('init', 'expected'):
    blocks = kernel.get(section, {}).get('memory', [])
    files = [block for block in blocks if 'file' in block]
    if not files:
        blockers.append(section + ' needs real capture file blocks')
    for block in files:
        if not (root / block['file']).is_file():
            blockers.append('missing capture file: ' + block['file'])
if 'TODO' in kernel.get('unit_of_work', {}).get('description', 'TODO'):
    blockers.append('define the captured call unit_of_work')
# The adapter supplies zero-filled unread memory by default. A real capture must
# cover all reads; never let that default hide a missing pointer or tree node.
kernel.pop('memory_default', None)
(root / 'audit.json').write_text(json.dumps({'blockers': sorted(set(blockers))}, indent=2) + '\n')
if blockers:
    print('\n'.join(sorted(set(blockers))))
kernel_path.write_text(json.dumps(kernel, indent=2) + '\n')
