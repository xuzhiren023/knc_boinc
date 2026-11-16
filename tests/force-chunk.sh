#!/usr/bin/env bash
# S5-02 acceptance. Optional first argument: pre-patch default binary.
set -euo pipefail
cd "$(dirname "$0")/.."
bash scripts/fetch.sh
export PATH="/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin:$PATH"
mkdir -p build/tmp
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
python tests/test_force_chunk.py
make -C mk -j6 x86 > build/force-chunk-default-build.log 2>&1
reference=${1:-build/x86/milkyway_nbody.exe}
for chunk in 1 4 16 128; do
    make -C mk -j6 TARGET=x86 OUT=../build/x86-chunk-$chunk FORCE_CHUNK=$chunk program > build/force-chunk-$chunk-build.log 2>&1
done
python tests/force_chunk_matrix.py "$reference" | tee build/force-chunk-comparison.txt
# Preserve this Git Bash interpreter after adding Cygwin tools to PATH.
"$BASH" packaging/make_package.sh > build/force-chunk-package.log 2>&1
python packaging/check_package.py dist/milkyway_package
"$BASH" scripts/card-check.sh | tee build/card-commands.txt
