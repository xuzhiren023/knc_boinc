#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin:$PATH"
mkdir -p build/tmp build/s11/checkpoint-cost
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
export OMP_NUM_THREADS=4
make -C mk -j2 checkpoint-cost
exe=$(cygpath -am build/x86/checkpoint_cost.exe)
(cd build/s11/checkpoint-cost; "$exe") | tee build/s11/checkpoint-cost.txt
