#!/usr/bin/env bash
# Capture/ref checks and supported diagnostic runs; no card execution.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/tmp
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
export PYTHONDONTWRITEBYTECODE=1
bash twin/capture_multicore.sh
bash scripts/run_x86.sh large 1 > build/s1-06-large-reference.log 2>&1
mkdir -p runs/x86/capture-large-1
cp build/s1-06-capture.hist runs/x86/capture-large-1/histogram.txt
cp build/s1-06-capture-stdout.txt runs/x86/capture-large-1/stdout.txt
cp build/s1-06-capture-stderr.txt runs/x86/capture-large-1/stderr.txt
cp build/s1-06-capture-exit.txt runs/x86/capture-large-1/exit.txt
python scripts/compare.py runs/x86/large-1 runs/x86/capture-large-1 > build/s1-06-capture-reference-compare.txt
bash scripts/run_x86.sh small 1 > build/s1-06-small-reference.log 2>&1
bash twin/run.sh > build/s1-06-gravity-region.log 2>&1
set +e
bash twin/run_multicore.sh > twin/multicore/run.log 2>&1
simulation_status=$?
set -e
cat twin/multicore/run.log
python twin/write_multicore_report.py
bash scripts/multicore-card-commands.sh > dist/card/multicore-commands.sh
python tests/test_twin_multicore.py
exit "$simulation_status"
