#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/tmp twin/flags
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
export PATH="/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin:$PATH"
export PYTHONDONTWRITEBYTECODE=1
make -C mk -j4 card > build/s5-01-card-build.log 2>&1
for variant in V0 V1 V2 V3; do
    make -C mk -f ../twin/flags.mk TARGET=card VARIANT="$variant" flag-variant > "build/s5-01-$variant-build.log" 2>&1
    python C:/Users/xuzhi/Documents/gcc_knc/tools/knc_lint "build/flags/$variant/milkyway_nbody.mic" > "build/flags/$variant/knc-lint.txt" 2>&1
    echo "$variant: rebuilt nbody_grav.c, linked unchanged baseline objects; knc_lint exit 0"
done
if [[ ! -f twin/multicore/capture.json ]]; then
    bash twin/capture_multicore.sh
fi
python twin/compare_flags.py
