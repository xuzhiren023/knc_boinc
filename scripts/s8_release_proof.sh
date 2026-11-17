#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/tmp build/s8-09
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
export PATH="/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin:$PATH"
export PYTHONDONTWRITEBYTECODE=1
source config/s8-09.env
make -C mk -j4 TARGET=x86 OUT=../build/s8-09/x86-final program > build/s8-09/release-rebuild.log 2>&1
python scripts/s8_integration.py matrix
