#!/usr/bin/env bash
# Pinned sources must already be present; no downloads, installs or card access.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/tmp
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
export PATH="/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin:$PATH"
export PYTHONDONTWRITEBYTECODE=1
for variant in off on; do
    flag=0
    [[ $variant != on ]] || flag=1
    options=()
    if [[ $variant == on ]]; then
        options+=('CFLAGS=-O2 -g -fopenmp -fno-strict-aliasing -ffp-contract=off -fno-math-errno -march=knc -std=gnu99 -fopt-info-vec-all')
    fi
    make -C mk -j4 TARGET=card OUT=../build/vector/card-$variant VECTOR_GRAVITY=$flag "${options[@]}" program > build/s6-card-$variant-build.log 2>&1
done
mkdir -p build/card
cp build/vector/card-off/milkyway_nbody.mic build/card/milkyway_nbody.mic
# Cygwin bash understands the package script's /cygdrive tool paths.
/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin/bash scripts/package_card.sh
for variant in off on; do
    mkdir -p dist/card/vector-$variant
    cp build/vector/card-$variant/milkyway_nbody.mic dist/card/vector-$variant/
    cp dist/card/*.so* dist/card/vector-$variant/
done
"$BASH" scripts/vector-card-commands.sh > dist/card/vector-commands.sh
