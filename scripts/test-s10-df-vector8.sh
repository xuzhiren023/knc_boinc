#!/usr/bin/env bash
# Retained acceptance by default. --measure runs only the authorized short cases.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/tmp build/s10/df-vector8
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
export PATH="/c/Program Files/Git/cmd:/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin:$PATH"
export PYTHONDONTWRITEBYTECODE=1 OMP_DYNAMIC=FALSE OMP_NUM_THREADS=4
base=build/s10/df-vector8
if [[ ${1:-} == --card ]]; then
    export S10_REQUIRE_CARD=1
fi
if [[ ${1:-} == --full ]]; then
    echo 'Owner canceled full host captures on 2026-11-17 19:45Z; use --measure for short cases.' >&2
    exit 2
fi
if [[ ${1:-} != --measure ]]; then
    python tests/test_s10_df_vector8.py
    exit
fi
python scripts/s8_patch_check.py > "$base/patch-replay.txt" 2>&1
python scripts/s8_patch_check.py --correctness-only > "$base/correctness-patch-replay.txt" 2>&1
for variant in release vector8 guard scalar scalar-guard; do
    bash scripts/build-s10-df-vector8.sh "$variant" x86
done
for variant in release vector8 guard scalar scalar-guard; do
    bash scripts/build-s10-df-vector8.sh "$variant" card
done
python scripts/s10-df-vector8.py stage window
for case in core-small real-steps; do
    for variant in release vector8 guard scalar scalar-guard; do
        python scripts/s10-df-vector8.py run "$variant" "$case"
    done
done
python scripts/s10-df-vector8.py differences
bash scripts/s10-df-vector8-compiler.sh
python scripts/s10-df-vector8.py stage
bash -n "$base/card-window.sh"
python tests/test_s10_df_vector8.py
