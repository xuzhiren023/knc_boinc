#!/usr/bin/env bash
# Offline S10-03 build; laptop load bounded to two compiler jobs.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/tmp build/s10/gen
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
shared=/c/Users/xuzhi/Documents/gcc_knc/.work/_shared
export PATH="/c/Program Files/Git/cmd:$shared/toolchain/cygwin/bin:$PATH"
export OMP_DYNAMIC=FALSE OMP_NUM_THREADS=12 PYTHONDONTWRITEBYTECODE=1
variant=${1:?variant}; target=${2:-x86}; profile=${3:-0}; candidate=${4:-0}
mkdir -p "build/s10/$variant"
opts=(TARGET="$target" OUT="../build/s10/$variant" OPTFLAGS=-O2
    TREE_VARIANT=2 DF_REUSE=1 PARALLEL_QUAD=1 STATIC_INTEGRATE=1 PHASE_TIMERS=1
    VECTOR_GRAVITY=0 FORCE_CHUNK=4 WALK_LAYOUT=0 TREE_IDENTITY=0 WALK_COUNTERS=0
    GEN_PROFILE="$profile" GEN_PIPELINE="$candidate")
common=base-profile
[[ $target != card ]] || common=card-profile
if [[ $variant == "$common" ]]; then
    make -C mk -j2 "${opts[@]}" program > "build/s10/gen/$variant-build.log" 2>&1
else
    make -C mk -f ../tests/s10-gen.mk -j2 "${opts[@]}" \
        COMMON_OUT="../build/s10/$common" gen-app > "build/s10/gen/$variant-build.log" 2>&1
fi
if [[ $target == x86 ]]; then
    python scripts/s10-gen.py prepare
    make -C mk -f ../tests/s10-gen.mk -j2 "${opts[@]}" \
        COMMON_OUT="../build/s10/$common" gen-capture \
        > "build/s10/gen/$variant-capture-build.log" 2>&1
else
    python C:/Users/xuzhi/Documents/gcc_knc/tools/knc_lint \
        "build/s10/$variant/milkyway_nbody.mic" > "build/s10/$variant/knc-lint.txt" 2>&1
    echo 'PASS: knc_lint exit 0' >> "build/s10/$variant/knc-lint.txt"
    mkdir -p build/s10/gen/runtimes
    for runtime in libgomp.so.1 libstdc++.so.6 libgcc_s.so.1; do
        cp -L "$shared/gcc-knc-16.2.0/k1om-mpss-linux/lib64/$runtime" build/s10/gen/runtimes/
    done
fi
echo "Built $variant"
