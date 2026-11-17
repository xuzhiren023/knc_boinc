#!/usr/bin/env bash
# --full is for a fresh worktree only: exactly one full run per variant.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/tmp build/s10/df-special
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
export PATH="/c/Program Files/Git/cmd:/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin:$PATH"
export PYTHONDONTWRITEBYTECODE=1 OMP_DYNAMIC=FALSE OMP_NUM_THREADS=12
base=build/s10/df-special
if [[ ${1:-} != --full ]]; then
    python tests/test_s10_df_special.py
    exit
fi
if compgen -G "$base/full-*-started.json" > /dev/null; then
    echo 'A full generation was already launched; use the retained acceptance test. No automatic reruns.' >&2
    exit 1
fi
python scripts/s8_patch_check.py > "$base/patch-replay.txt" 2>&1
for variant in release special vmath; do
    bash scripts/build-s10-df-special.sh "$variant" x86
    python scripts/s10-df-special.py run "$variant"
done
python scripts/s10-df-special.py exact
# Finish compiler work before the long, serial host experiments.
for variant in release special vmath; do
    bash scripts/build-s10-df-special.sh "$variant" card
done
python scripts/s10-df-special.py run special full
python scripts/s10-df-special.py run vmath full
python scripts/s10-df-special.py differences
python scripts/s10-df-special.py stage
bash -n "$base/card-window.sh"
python tests/test_s10_df_special.py
