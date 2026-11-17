#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/tmp build/s10/df-batch
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
drive=/c
[[ ! -d /cygdrive/c ]] || drive=/cygdrive/c
export PATH="$drive/Program Files/Git/cmd:$drive/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin:$PATH"
export PYTHONDONTWRITEBYTECODE=1 OMP_DYNAMIC=FALSE OMP_NUM_THREADS=4
base=build/s10/df-batch
case ${1:-} in
    --card) export S10_REQUIRE_CARD=1;;
    --measure)
        python scripts/s8_patch_check.py > "$base/patch-replay.txt" 2>&1
        python scripts/s8_patch_check.py --correctness-only > "$base/correctness-patch-replay.txt" 2>&1
        for target in x86 card; do
            for variant in release batch; do bash scripts/build-s10-df-batch.sh "$variant" "$target"; done
        done
        for case in core-small real-steps; do
            for variant in release batch; do python scripts/s10-df-batch.py run "$variant" "$case"; done
        done
        python scripts/s10-df-batch.py proof
        python scripts/twin-s10-df-batch.py
        python scripts/model-s10-df-batch.py
        python scripts/s10-df-batch.py stage
        bash -n "$base/card-window.sh";;
    '') ;;
    *) echo 'Use --measure or --card; full 117676 host runs are excluded.' >&2;exit 2;;
esac
python tests/test_s10_df_batch.py
