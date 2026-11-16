"""Record the installed twin's functional support before replaying the walk."""
import json
import os
from pathlib import Path
import sys
cap = json.loads(Path('build/s6-capabilities/capabilities.json').read_text())
ops = {r['mnemonic']: r for r in cap['instructions']}
required = ['vrcp23ps', 'vrsqrt23ps', 'vfmadd231pd', 'vfnmadd231pd']
report = {'engine_version': cap['engine_version'],
          'required_functional_support': all(ops.get(op, {}).get('functional') for op in required),
          'instructions': {op: ops.get(op) for op in required},
          'seed_policy': 'Native seed bit patterns need captured tables; default seed values are approximate.',
          'scalar_baseline': ('enabled after S14-37 verification' if os.environ.get('TWIN_SCALAR_READY') == '1' else 'not rerun: installed S14-37 repro still mismatches; see s14-37-check.json')}
Path('twin/vector/capabilities.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
sys.exit(0 if report['required_functional_support'] else 1)
