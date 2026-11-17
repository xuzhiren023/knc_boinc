#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/tmp build/s10-memory
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
shared=/c/Users/xuzhi/Documents/gcc_knc/.work/_shared
export PATH="$shared/toolchain/cygwin/bin:$PATH" PYTHONDONTWRITEBYTECODE=1
source config/release.env
for target in "${1:-x86}"; do
    for variant in base order huge both; do
        order=0 huge=0 proof=0
        case $variant in order) order=1;; huge) huge=1;; both) order=1; huge=1;; esac
        [[ $target != x86 ]] || proof=1
        folder="build/s10-memory/$target-$variant"
        if [[ $variant != base && ! -d $folder ]]; then
            python scripts/seed-s10-memory.py "$target-base" "$target-$variant" "$order" "$huge" 0
        fi
        mkdir -p "$folder"
        make -C mk -j2 TARGET="$target" OUT="../$folder" WALK_ORDER="$order" \
            WALK_HUGEPAGES="$huge" WALK_PROOF="$proof" PHASE_TIMERS=1 \
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
    mkdir -p build/s10-memory/runtimes
    for lib in libstdc++.so.6 libgcc_s.so.1 libgomp.so.1; do
        cp -L "$shared/gcc-knc-16.2.0/k1om-mpss-linux/lib64/$lib" build/s10-memory/runtimes/
    done
fi
if [[ ${1:-x86} == card ]]; then
    folder=build/s10-memory/card-pages
    if [[ ! -d $folder ]]; then
        python scripts/seed-s10-memory.py card-both card-pages 1 1 1
    fi
    make -C mk -j2 TARGET=card OUT="../$folder" WALK_ORDER=1 WALK_HUGEPAGES=1 \
        WALK_MEMORY_PROOF=1 PHASE_TIMERS=1 program > "$folder/build.log" 2>&1
    python C:/Users/xuzhi/Documents/gcc_knc/tools/knc_lint \
        "$folder/milkyway_nbody.mic" > "$folder/knc-lint.txt" 2>&1
    echo 'PASS: knc_lint exit 0' >> "$folder/knc-lint.txt"
    "$shared/gcc-knc-16.2.0/bin/k1om-mpss-linux-gcc" -O2 -march=knc \
        probes/s10_memory_affinity.c -o build/s10-memory/walk-affinity.mic
    python C:/Users/xuzhi/Documents/gcc_knc/tools/knc_lint \
        build/s10-memory/walk-affinity.mic > build/s10-memory/affinity-lint.txt 2>&1
    echo 'Built card-pages and sibling affinity helper'
fi
# Audit the exact snapshot ABI on both targets, without running the card.
compiler="$shared/toolchain/cygwin/bin/gcc"
[[ ${1:-x86} != card ]] || compiler="$shared/gcc-knc-16.2.0/bin/k1om-mpss-linux-gcc"
"$compiler" -O2 -S -DNBODY_WALK_HOT=0 -DDOUBLEPREC=1 -DDSFMT_MEXP=19937 \
    -DHAVE_CONFIG_H -Iconfig -Ithird_party/milkywayathome_client_196/nbody/include \
    -Ithird_party/milkywayathome_client_196/milkyway/include \
    -Ithird_party/milkywayathome_client_196/lua/src -Ithird_party/milkywayathome_client_196/lua/include \
    -Ithird_party/milkywayathome_client_196/popt/include -Ithird_party/milkywayathome_client_196/dSFMT \
    -Ithird_party/milkywayathome_client_196/crlibm probes/s10_walk_layout.c \
    -o "build/s10-memory/layout-${1:-x86}.s"
if [[ ${1:-x86} == card ]]; then
    bash scripts/build-s10-memory-release.sh
fi
