#!/usr/bin/env bash
# Host-only diagnostics. Nonzero statuses are retained, never converted to a pass.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONDONTWRITEBYTECODE=1
TWIN_HOME=${TWIN_HOME:-C:/Users/xuzhi/.claude/skills/knc-twin}
cli="$TWIN_HOME/scripts/knc_twin.py"
python twin/prepare_multicore.py
failed=0
for scale in core unit ring; do
    echo "\$ python $cli simulate twin/multicore/$scale.json --scale $scale --profile card-7120-measured --max-steps 2000000 --max-seconds 1740 --no-issue-log --out twin/multicore/$scale --force"
    rm -f "twin/multicore/$scale/result.json"
    timeout 1790s python "$cli" simulate "twin/multicore/$scale.json" --scale "$scale" \
        --profile card-7120-measured --max-steps 2000000 --max-seconds 1740 \
        --no-issue-log --out "twin/multicore/$scale" --force || failed=1
done
for scale in unit ring; do
    echo "\$ python $cli compare twin/multicore/core/result.json twin/multicore/$scale/result.json --out twin/multicore/compare-$scale --force"
    python "$cli" compare twin/multicore/core/result.json "twin/multicore/$scale/result.json" \
        --out "twin/multicore/compare-$scale" --force || failed=1
done
exit "$failed"
