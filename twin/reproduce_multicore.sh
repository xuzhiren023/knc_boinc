#!/usr/bin/env bash
# S1-07 host reproduction. Known model failures are retained and checked.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/tmp
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
export PYTHONDONTWRITEBYTECODE=1
bash twin/capture_multicore.sh
bash twin/replay_x87.sh > build/s1-07-x87.log 2>&1
set +e
bash twin/isolate_multicore.sh > build/s1-07-isolation.log 2>&1
isolation_status=$?
set -e
[[ "$isolation_status" == 6 ]] # exact functional mismatch from the minimal repro
python twin/check_x87_replay.py
set +e
CHUNK_MAX_SECONDS=60 bash twin/run_chunks.sh 128 > build/s1-07-chunks128.log 2>&1
full_status=$?
set -e
[[ "$full_status" == 1 ]]
python twin/summarize_chunks.py full-chunk-attempt.json
set +e
bash twin/run_chunks.sh 2 > build/s1-07-chunks2.log 2>&1
diagnostic_status=$?
set -e
[[ "$diagnostic_status" == 1 ]]
python twin/summarize_chunks.py chunk-evidence.json
python twin/write_s1_07_report.py
bash scripts/multicore-card-commands.sh > dist/card/multicore-commands.sh
python tests/test_twin_multicore.py
