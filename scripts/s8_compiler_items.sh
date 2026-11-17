#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/tmp build/s8-09/compiler-item
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
export PATH="/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin:$PATH"
cc=/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/gcc-knc-16.2.0/bin/k1om-mpss-linux-gcc
for variant in opaque readonly; do
    option=()
    [[ $variant != readonly ]] || option=(-DSAMPLES_READ_ONLY)
    "$cc" -O3 -march=knc -ffp-contract=off -fno-math-errno "${option[@]}" \
        -fopt-info-vec-missed="build/s8-09/compiler-item/df-$variant-missed.txt" \
        -S probes/s8_df_reuse.c -o "build/s8-09/compiler-item/df-$variant.s"
done
"$cc" -O2 -march=knc -fprefetch-loop-arrays -fno-math-errno -ffp-contract=off \
    -fopt-info-vec-missed=build/s8-09/compiler-item/walk-prefetch-missed.txt \
    -S probes/walk-prefetch.c -o build/s8-09/compiler-item/walk-prefetch.s
