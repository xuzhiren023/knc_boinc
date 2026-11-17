#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/s9-common.sh
for target in x86 card; do
    identity=0
    [[ $target != x86 ]] || identity=1
    folder="build/s9/$target-tree4"
    mkdir -p "$folder"
    make -C mk -j2 TARGET="$target" OUT="../$folder" \
        TREE_VARIANT=4 PARALLEL_QUAD=1 STATIC_INTEGRATE=1 PHASE_TIMERS=1 \
        VECTOR_GRAVITY=0 FORCE_CHUNK=4 WALK_LAYOUT=0 TREE_IDENTITY="$identity" \
        WALK_COUNTERS=0 OPTFLAGS=-O2 program > "$folder/build.log" 2>&1
    if [[ $target == card ]]; then
        python C:/Users/xuzhi/Documents/gcc_knc/tools/knc_lint \
            "$folder/milkyway_nbody.mic" > "$folder/knc-lint.txt" 2>&1
        echo 'PASS: knc_lint exit 0' >> "$folder/knc-lint.txt"
    fi
    echo "Built $target-tree4"
done
mkdir -p build/s9/runtimes
for lib in libstdc++.so.6 libgcc_s.so.1 libgomp.so.1; do
    cp -L "$S9_SHARED/gcc-knc-16.2.0/k1om-mpss-linux/lib64/$lib" build/s9/runtimes/
done
python scripts/s9-tree4.py stage
cat build/s9/tree4-window.sh
