#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/tmp build/s10-walk
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
export PATH="/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin:$PATH"
export PYTHONDONTWRITEBYTECODE=1
bash scripts/build-s10-walk.sh x86
python scripts/capture-s10-walk.py
python scripts/s10-walk.py proof | tee build/s10-walk/proof-run.log
python scripts/s10-walk.py rank | tee build/s10-walk/rank-run.log
bash scripts/build-s10-walk.sh card
bash scripts/s10-walk-compiler.sh
python scripts/twin-s10-walk.py | tee build/s10-walk/twin-run.log
python scripts/s10-walk.py stage
PATH="/c/Program Files/Git/cmd:$PATH" python scripts/s8_patch_check.py > build/s10-walk/patch-check.txt
PATH="/c/Program Files/Git/cmd:$PATH" python scripts/s8_patch_check.py --correctness-only > build/s10-walk/correctness-only.txt
python tests/test_s10_walk.py 2>&1 | tee build/s10-walk/acceptance-after.txt
