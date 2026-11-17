#!/usr/bin/env bash
# Build and lint only. The lead runs scripts/quad-card-command.sh's output.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/tmp build/s8/card-quad
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
export PATH="/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin:$PATH"
make -C mk -j4 TARGET=card OUT=../build/s8/card-quad \
    PARALLEL_QUAD=1 VECTOR_GRAVITY=0 FORCE_CHUNK=4 program \
    > build/s8/card-quad/build.log 2>&1
mkdir -p build/card
cp build/s8/card-quad/milkyway_nbody.mic build/card/
C:/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin/bash.exe scripts/package_card.sh
cp dist/card/knc-lint.txt build/s8/card-quad/
bash scripts/quad-card-command.sh > build/s8/card-quad/card-command.sh
