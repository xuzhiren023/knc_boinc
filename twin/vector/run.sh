#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")/../.."
export PYTHONDONTWRITEBYTECODE=1
TWIN_HOME=${TWIN_HOME:-C:/Users/xuzhi/.claude/skills/knc-twin}
failed=0
for first in 0 1024; do
    for variant in vector scalar; do
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
