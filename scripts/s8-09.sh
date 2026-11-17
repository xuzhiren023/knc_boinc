#!/usr/bin/env bash
# Offline integration driver. Never contacts the card or writes Git metadata.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/tmp build/s8-09
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
cyg=/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin
export PATH="/c/Program Files/Git/cmd:$cyg:$PATH" PYTHONDONTWRITEBYTECODE=1
source config/s8-09.env
case "${1:-build}" in
    build)
        make -C mk -j4 TARGET=x86 OUT=../build/s8-09/x86-final program > build/s8-09/x86-final-build.log 2>&1
        make -C mk -j4 TARGET=card program > build/s8-09/card-build.log 2>&1
        # This packaging entry point uses /c paths; retain Git Bash even though
        # the compiler/make PATH correctly prefers the supplied Cygwin tools.
        '/c/Program Files/Git/bin/bash.exe' packaging/make_package.sh > build/s8-09/package-build.log 2>&1
        mkdir -p build/s8-09/card
        cp build/card/milkyway_nbody.mic dist/card/knc-lint.txt build/s8-09/card/
        python scripts/s8_integration.py manifest
        python scripts/s8_integration.py stage
        ;;
    proof) python scripts/s8_integration.py proof "${@:2}" ;;
    stock) python scripts/s8_integration.py stock ;;
    stage) python scripts/s8_integration.py stage ;;
    verify) python tests/test_s8_integration.py "${@:2}" ;;
    *) echo 'usage: bash scripts/s8-09.sh build|proof|stock|stage|verify [--host]' >&2; exit 2 ;;
esac
