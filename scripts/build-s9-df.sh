#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/s9-df-common.sh
variant=${1:?variant}; target=${2:-x86}; reuse=${3:-0}; vector=${4:-0}
mkdir -p "build/s9/$variant"
experiment=()
if [[ $vector == 1 ]]; then
    python scripts/s9-df.py experiment
    experiment=(DF_SOURCE=../build/s9/df/experiment-tree/nbody/src/nbody_mixeddwarf.c)
fi
make -C mk -j2 TARGET="$target" OUT="../build/s9/$variant" \
    TREE_VARIANT=2 PARALLEL_QUAD=1 STATIC_INTEGRATE=1 PHASE_TIMERS=1 \
    VECTOR_GRAVITY=0 FORCE_CHUNK=4 WALK_LAYOUT=0 TREE_IDENTITY=0 WALK_COUNTERS=0 \
    OPTFLAGS=-O2 DF_REUSE="$reuse" DF_VECTOR="$vector" DF_STATS="$vector" \
    "${experiment[@]}" program > "build/s9/df/$variant-build.log" 2>&1
if [[ $target == x86 ]]; then
    python scripts/s9-df.py prepare "$vector"
    make -C mk -f ../tests/s9-df.mk -j2 TARGET=x86 OUT="../build/s9/$variant" \
        TREE_VARIANT=2 PARALLEL_QUAD=1 STATIC_INTEGRATE=1 PHASE_TIMERS=1 \
        VECTOR_GRAVITY=0 FORCE_CHUNK=4 WALK_LAYOUT=0 TREE_IDENTITY=0 WALK_COUNTERS=0 \
        OPTFLAGS=-O2 DF_REUSE="$reuse" DF_VECTOR="$vector" DF_STATS="$vector" \
        "${experiment[@]}" DF_CAPTURE_SOURCE=../build/s9/df/mixeddwarf-capture.c df-capture \
        > "build/s9/df/$variant-capture-build.log" 2>&1
else
    python C:/Users/xuzhi/Documents/gcc_knc/tools/knc_lint \
        "build/s9/$variant/milkyway_nbody.mic" > "build/s9/$variant/knc-lint.txt" 2>&1
    mkdir -p build/s9/df/runtimes
    for runtime in libgomp.so.1 libstdc++.so.6 libgcc_s.so.1; do
        cp -L "$S9_DF_SHARED/gcc-knc-16.2.0/k1om-mpss-linux/lib64/$runtime" build/s9/df/runtimes/
    done
    echo 'PASS: knc_lint exit 0' >> "build/s9/$variant/knc-lint.txt"
fi
echo "Built $variant"
