#!/usr/bin/env bash
# Offline S8 build. Git Bash entry point, Cygwin make/compiler tools.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/tmp build/s8
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
export PATH="/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin:$PATH"
for variant in card-timers card-timers-static x86-timers; do
    target=card
    static=0
    [[ $variant != x86-timers ]] || target=x86
    [[ $variant != card-timers-static ]] || static=1
    make -C mk -j4 TARGET="$target" OUT="../build/s8/$variant" VECTOR_GRAVITY=0 \
        PHASE_TIMERS=1 STATIC_INTEGRATE="$static" program > "build/s8/$variant-build.log" 2>&1
    echo "Built build/s8/$variant"
done
