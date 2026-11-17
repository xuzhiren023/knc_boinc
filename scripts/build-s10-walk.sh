#!/usr/bin/env bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
cd "$(dirname "$0")/.."
mkdir -p build/tmp build/s10-walk
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
shared=/c/Users/xuzhi/Documents/gcc_knc/.work/_shared
export PATH="$shared/toolchain/cygwin/bin:$PATH"
# S10-01 release configuration is not present: exact S9-06 fallback.
for target in "${1:-x86}"; do
    for variant in base prefetch hot both profile4 profile1 guided; do
        prefetch=0 hot=0 profile=0 schedule=0 proof=0
        case $variant in prefetch) prefetch=1;; hot) hot=1;; both) prefetch=1; hot=1;;
            profile4) profile=1;; profile1) profile=1; schedule=1;; guided) profile=1; schedule=2;; esac
        [[ $target != x86 ]] || proof=1
        folder="build/s10-walk/$target-$variant"
        # Only gravity uses PROFILE/PREFETCH/SCHEDULE/PROOF; HOT affects ABI.
        # Reuse within a freshly built same-HOT family, always recompile gravity.
        seed=base
        [[ $hot == 0 ]] || seed=hot
        if [[ ! -d $folder && $variant != "$seed" && -d build/s10-walk/$target-$seed ]]; then
            python scripts/s10-walk-seed.py "$target-$seed" "$target-$variant"                 "WALK_PROFILE=$profile" "WALK_PREFETCH=$prefetch"                 "WALK_SCHEDULE=$schedule" "WALK_PROOF=$proof"
        fi
        mkdir -p "$folder"
        make -C mk -j2 TARGET="$target" OUT="../$folder" TREE_VARIANT=4 \
            PARALLEL_QUAD=1 STATIC_INTEGRATE=1 FORCE_CHUNK=4 OPTFLAGS=-O2 \
            DF_REUSE=0 VECTOR_GRAVITY=0 WALK_LAYOUT=0 WALK_COUNTERS=0 TREE_IDENTITY=0 \
            PHASE_TIMERS=1 WALK_PREFETCH="$prefetch" WALK_HOT="$hot" \
            WALK_PROFILE="$profile" WALK_SCHEDULE="$schedule" WALK_PROOF="$proof" \
            program > "$folder/build.log" 2>&1
        if [[ $target == card ]]; then
            python C:/Users/xuzhi/Documents/gcc_knc/tools/knc_lint \
                "$folder/milkyway_nbody.mic" > "$folder/knc-lint.txt" 2>&1
            echo 'PASS: knc_lint exit 0' >> "$folder/knc-lint.txt"
        fi
        echo "Built $target-$variant"
    done
done
if [[ ${1:-x86} == card ]]; then
    mkdir -p build/s10-walk/runtimes
    for lib in libstdc++.so.6 libgcc_s.so.1 libgomp.so.1; do
        cp -L "$shared/gcc-knc-16.2.0/k1om-mpss-linux/lib64/$lib" build/s10-walk/runtimes/
    done
fi
