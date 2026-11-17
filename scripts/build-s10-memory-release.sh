#!/usr/bin/env bash
# Exact release.env controls, distinct from the phase-timed card window copies.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/tmp build/s10-memory
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
shared=/c/Users/xuzhi/Documents/gcc_knc/.work/_shared
export PATH="$shared/toolchain/cygwin/bin:$PATH" PYTHONDONTWRITEBYTECODE=1
source config/release.env
for variant in base order huge both; do
    order=0 huge=0
    case $variant in order) order=1;; huge) huge=1;; both) order=1; huge=1;; esac
    folder="build/s10-memory/card-release-$variant"
    if [[ $variant != base && ! -d $folder ]]; then
        python scripts/seed-s10-memory.py card-release-base "card-release-$variant" "$order" "$huge" 0
    fi
    mkdir -p "$folder"
    make -C mk -j2 TARGET=card OUT="../$folder" WALK_ORDER="$order" \
        WALK_HUGEPAGES="$huge" WALK_PROOF=0 PHASE_TIMERS=0 \
        program > "$folder/build.log" 2>&1
    python C:/Users/xuzhi/Documents/gcc_knc/tools/knc_lint \
        "$folder/milkyway_nbody.mic" > "$folder/knc-lint.txt" 2>&1
    echo 'PASS: knc_lint exit 0' >> "$folder/knc-lint.txt"
    echo "Built exact release card-release-$variant"
done
