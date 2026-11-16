#!/usr/bin/env bash
# Re-extract the whole built function; preserve non-ok results as evidence.
set -euo pipefail
cd "$(dirname "$0")/.."
TWIN_HOME=${TWIN_HOME:-C:/Users/xuzhi/.claude/skills/knc-twin}
OBJDUMP=${KNC_OBJDUMP:-C:/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cross/bin/k1om-mpss-linux-objdump.exe}
function_name=${1:-nbGravity}
capture=${2:-twin/capture.json}
binary=build/card/milkyway_nbody.mic
python "$TWIN_HOME/scripts/knc_twin.py" capabilities --out twin/capabilities --force
"$OBJDUMP" -dr "$binary" > twin/card.disassembly.txt
python "$TWIN_HOME/scripts/from_binary.py" "$binary" --function "$function_name" \
    --with-callee nbReportTreeIncest --disassembly twin/card.disassembly.txt --init "$capture" \
    --out twin/kernel.json --report twin/conversion.json
# The transitive library inclusion is attempted faithfully. The adapter refuses
# the PLT's indirect jump: keep the diagnostic; never strip the branch or invent costs.
set +e
python "$TWIN_HOME/scripts/from_binary.py" "$binary" --function "$function_name" \
    --with-callee nbReportTreeIncest --with-callee sqrt@plt --with-callee fprintf@plt \
    --disassembly twin/card.disassembly.txt --init "$capture" \
    --out twin/closure.json --report twin/closure-conversion.json > twin/closure-attempt.txt 2>&1
closure_status=$?
set -e
printf 'adapter_exit=%s\n' "$closure_status" >> twin/closure-attempt.txt
# Audit records the blockers. Commands below independently return their actual
# unsupported status, without evaluating an approximate or truncated trace.
python twin/check_kernel.py
failed=0
for command in validate functional simulate bounds; do
    options=()
    if [[ "$command" != functional ]]; then options+=(--profile card-7120-measured); fi
    python "$TWIN_HOME/scripts/knc_twin.py" "$command" twin/kernel.json \
        "${options[@]}" --out "twin/$command" --force || failed=1
done
exit "$failed"
