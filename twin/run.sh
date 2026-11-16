#!/usr/bin/env bash
# Extract the built function, then end the region before its cold error block.
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
cd "$(dirname "$0")/.."
TWIN_HOME=${TWIN_HOME:-C:/Users/xuzhi/.claude/skills/knc-twin}
OBJDUMP=${KNC_OBJDUMP:-C:/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cross/bin/k1om-mpss-linux-objdump.exe}
function_name=${1:-nbGravity}
capture=${2:-twin/capture.json}
binary=build/card/milkyway_nbody.mic
python twin/check_reference.py
python "$TWIN_HOME/scripts/knc_twin.py" capabilities --out twin/capabilities --force
"$OBJDUMP" -dr "$binary" > twin/card.disassembly.txt
python "$TWIN_HOME/scripts/from_binary.py" "$binary" --function "$function_name" \
    --disassembly twin/card.disassembly.txt --init "$capture" \
    --out twin/gravity-full.json --report twin/conversion.json
python twin/cut_gravity.py
python twin/check_kernel.py
failed=0
for command in validate functional simulate bounds; do
    options=()
    if [[ "$command" == functional ]]; then options+=(--trace); fi
    if [[ "$command" != functional ]]; then options+=(--profile card-7120-measured); fi
    python "$TWIN_HOME/scripts/knc_twin.py" "$command" twin/kernel.json \
        "${options[@]}" --out "twin/$command" --force || failed=1
done
python - <<'PY_CHECK'
import json
from pathlib import Path
trace = json.loads(Path('twin/functional/trace.json').read_text())
rows = trace['0']
assert all(row['id'] != 'cold_error_exit' for row in rows), 'captured input reached excluded error path'
kernel = json.loads(Path('twin/kernel.json').read_text())
label = kernel['provenance']['region_cut']['exit_label']
branches = {row['id'] for row in kernel['streams'][0]['instructions'] if row['ops'] == [label]}
observed = [row for row in rows if row['id'] in branches]
assert observed and all(row['taken'] is False for row in observed)
evidence = {'dynamic_instructions': len(rows), 'cold_exit_executed': False,
            'error_branches': observed, 'normal_return_executed': any(row['op'] == 'ret' for row in rows)}
assert evidence['normal_return_executed']
Path('twin/gravity-execution.json').write_text(json.dumps(evidence, indent=2)+chr(10))
print('Gravity trace: cold_error_exit absent; normal return/output stores retained')
PY_CHECK
exit "$failed"
