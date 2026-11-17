#!/usr/bin/env bash
# Build the exact release and its measurement twin; no card access.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/tmp build/s10
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
export PATH="/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin:$PATH"
source config/release.env
for variant in card-release card-release-timers; do
    timers=0
    [[ $variant != card-release-timers ]] || timers=1
    mkdir -p "build/s10/$variant"
    make -C mk -j2 TARGET=card OUT="../build/s10/$variant" PHASE_TIMERS="$timers" program \
        > "build/s10/$variant/build.log" 2>&1
    python C:/Users/xuzhi/Documents/gcc_knc/tools/knc_lint \
        "build/s10/$variant/milkyway_nbody.mic" > "build/s10/$variant/knc-lint.txt" 2>&1
    echo 'PASS: knc_lint exit 0' >> "build/s10/$variant/knc-lint.txt"
    echo "Built $variant"
done
