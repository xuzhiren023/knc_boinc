#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/tmp build/s10-memory
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
shared=/c/Users/xuzhi/Documents/gcc_knc/.work/_shared
export PATH="$shared/toolchain/cygwin/bin:$PATH" PYTHONDONTWRITEBYTECODE=1
python scripts/model-s10-memory.py > build/s10-memory/model.txt
bash scripts/build-s10-memory.sh x86
python scripts/capture-s10-memory.py > build/s10-memory/capture.txt
python scripts/s10-memory.py proof > build/s10-memory/proof.txt
bash scripts/build-s10-memory.sh card
python scripts/twin-s10-memory.py > build/s10-memory/twin-run.txt
PATH="/c/Program Files/Git/cmd:$PATH" python scripts/s8_patch_check.py > build/s10-memory/patch-check.txt
PATH="/c/Program Files/Git/cmd:$PATH" python scripts/s8_patch_check.py --correctness-only > build/s10-memory/correctness-only.txt
python scripts/s10-memory.py stage
python tests/test_s10_memory.py > build/s10-memory/acceptance-after.txt 2>&1
cat build/s10-memory/acceptance-after.txt
