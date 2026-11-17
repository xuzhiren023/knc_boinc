#!/usr/bin/env bash
# Four release identity cases at 12 threads, one generation-only capture,
# and one separate instrumented large tree-check run. No timing sweeps.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/tmp build/s10/x86-release build/s10/x86-identity
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
export PATH="/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin:$PATH"
export PYTHONDONTWRITEBYTECODE=1
source config/release.env
make -C mk -j2 TARGET=x86 OUT=../build/s10/x86-release program > build/s10/x86-release/build.log 2>&1
python scripts/s10-release.py prepare
make -C mk -f ../tests/s9-df.mk -j2 TARGET=x86 OUT=../build/s10/x86-release \
    DF_CAPTURE_SOURCE=../build/s10/mixeddwarf-capture.c df-capture > build/s10/capture-build.log 2>&1
make -C mk -j2 TARGET=x86 OUT=../build/s10/x86-identity TREE_IDENTITY=1 PHASE_TIMERS=1 program \
    > build/s10/x86-identity/build.log 2>&1
python scripts/s10-release.py proof > build/s10/proof.txt 2>&1
python scripts/s10-release.py stage
python tests/test_s10_release.py > build/s10/acceptance-green.txt 2>&1
cat build/s10/proof.txt build/s10/acceptance-green.txt
