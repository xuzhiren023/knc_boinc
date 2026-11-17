#!/usr/bin/env bash
# Print the local runner's absolute path; no booking or card execution.
# For staged S9-01 build/s9/{pgo-train,card-threads}.sh, replace
# python C:/Users/xuzhi/Documents/gcc_knc/tools/card_run with:
# python "$(bash /path/to/knc-boinc/scripts/card-run-path.sh)"
# Use the checkout containing S9-02 after the lead lands it; preserve the staged
# script's working directory and every other argument. See tools/CARD_RUN.md.
set -euo pipefail
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
printf '%s/tools/card_run\n' "$root"
