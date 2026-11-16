#!/usr/bin/env bash
# Functional first; preserve approximate/unsupported statuses, never use partial cycles.
set -uo pipefail
cd "$(dirname "$0")/../.."
export PYTHONDONTWRITEBYTECODE=1
TWIN_HOME=${TWIN_HOME:-C:/Users/xuzhi/.claude/skills/knc-twin}
python "$TWIN_HOME/scripts/knc_twin.py" capabilities --out build/s6-capabilities --force || exit
python twin/vector/check_capabilities.py || exit
failed=0
variants=(vector)
# Set only after verifying S14-37 landed in the installed twin.
[[ ${TWIN_SCALAR_READY:-0} != 1 ]] || variants+=(scalar)
for first in 0 1024 2048 4088; do
    for variant in "${variants[@]}"; do
        for mode in functional simulate; do
            options=(--max-steps 2000000 --max-seconds 900)
            if [[ $mode == functional ]]; then options+=(--trace); else options+=(--profile card-7120-measured --no-issue-log); fi
            cmd=(python "$TWIN_HOME/scripts/knc_twin.py" "$mode" "twin/vector/$variant-$first.json"
                 "${options[@]}" --out "twin/vector/$variant-$first-$mode" --force)
            printf '$ %s\n' "${cmd[*]}"
            "${cmd[@]}" || failed=1
        done
    done
done
exit "$failed"
