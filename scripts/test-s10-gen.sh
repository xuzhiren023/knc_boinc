#!/usr/bin/env bash
# Fresh worktree reproduction requires --full (one final full generation);
# once full-started.json exists, use the retained-proof acceptance test instead.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/tmp build/s10/gen
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
export PATH="/c/Program Files/Git/cmd:/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin:$PATH"
export PYTHONDONTWRITEBYTECODE=1 OMP_DYNAMIC=FALSE OMP_NUM_THREADS=12
if [[ ${1:-} != --full && ! -e build/s10/gen/full-proof.json ]]; then
    echo 'A fresh worktree needs --full; retained evidence can be checked with python tests/test_s10_gen.py.' >&2
    exit 1
fi
if [[ ${1:-} == --full && -e build/s10/gen/full-started.json ]]; then
    echo 'Full generation was already launched; run python tests/test_s10_gen.py for retained proofs.' >&2
    exit 1
fi
python scripts/s8_patch_check.py > build/s10/gen/patch-replay.txt 2>&1
for spec in base-profile:1:0 selected-profile:1:1 selected:0:1; do
    IFS=: read -r variant profile pipeline <<< "$spec"
    bash scripts/build-s10-gen.sh "$variant" x86 "$profile" "$pipeline"
    python scripts/s10-gen.py run "$variant"
done
python scripts/s10-gen.py core
python scripts/s10-gen.py select
if [[ ${1:-} == --full ]]; then
    python scripts/s10-gen.py full
fi
for spec in card-profile:1:0 card-selected:1:1 card-selected-clean:0:1; do
    IFS=: read -r variant profile pipeline <<< "$spec"
    bash scripts/build-s10-gen.sh "$variant" card "$profile" "$pipeline"
done
python scripts/s10-gen.py stage
bash -n build/s10/gen/card-window.sh
python tests/test_s10_gen.py
