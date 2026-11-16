#!/usr/bin/env bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
cd "$(dirname "$0")/.."
mkdir -p build/tmp
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
export PATH="/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin:$PATH"
make -C mk -j4 card
make -C mk -j4 x86
bash probes/build.sh
bash scripts/run_x86.sh 'small medium large'
# Negative findings must still produce envelopes for all four commands.
set +e
bash twin/run.sh
bash twin/run_hot.sh
set -e
python twin/diagnose_log.py
python twin/write_report.py
python tests/test_libm_probe.py
python tests/test_twin.py
