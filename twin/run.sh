#!/usr/bin/env bash
# Re-extract the whole built function; preserve non-ok results as evidence.
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
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
# Include the PLT entries that actually exist in this build. In particular,
# -fno-math-errno removes sqrt@plt; its absence must not mask the fprintf test.
closure_callees=()
for symbol in sqrt@plt fprintf@plt; do
    if grep -Fq "<$symbol>:" twin/card.disassembly.txt; then
        closure_callees+=(--with-callee "$symbol")
    fi
done
set +e
python "$TWIN_HOME/scripts/from_binary.py" "$binary" --function "$function_name" \
    --with-callee nbReportTreeIncest "${closure_callees[@]}" \
    --disassembly twin/card.disassembly.txt --init "$capture" \
    --out twin/closure.json --report twin/closure-conversion.json > twin/closure-attempt.txt 2>&1
closure_status=$?
set -e
printf 'adapter_exit=%s\n' "$closure_status" >> twin/closure-attempt.txt
# No branch deletion or invented cost for the unsupported closure.
python twin/check_kernel.py
failed=0
for command in validate functional simulate bounds; do
    options=()
    if [[ "$command" != functional ]]; then options+=(--profile card-7120-measured); fi
    python "$TWIN_HOME/scripts/knc_twin.py" "$command" twin/kernel.json \
        "${options[@]}" --out "twin/$command" --force || failed=1
done
exit "$failed"
