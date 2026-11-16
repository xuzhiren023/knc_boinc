#!/usr/bin/env bash
# Prints commands only; the lead runs the card.
set -euo pipefail
cd "$(dirname "$0")/.."
[[ -f dist/card/libm_probe.mic ]] || { echo 'Run bash probes/build.sh first' >&2; exit 1; }
command=(python C:/Users/xuzhi/Documents/gcc_knc/tools/card_run --threads 1 --timeout 300
 --receipt runs/card/libm-probe.json --file dist/card/libm_probe.mic --file twin/capture/log-input.bin)
for runtime in dist/card/*.so*; do command+=(--file "$runtime"); done
command+=(scripts/probe-launch.sh)
printf '%q ' "${command[@]}"
printf '> runs/card/libm-probe.txt 2> runs/card/libm-probe.stderr\n'
printf '%s\n' 'python scripts/compare_probe.py runs/probe/x86.txt runs/card/libm-probe.txt'
