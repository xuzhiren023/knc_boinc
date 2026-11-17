#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/tmp build/s10/df-batch
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
drive=/c
[[ ! -d /cygdrive/c ]] || drive=/cygdrive/c
shared="$drive/Users/xuzhi/Documents/gcc_knc/.work/_shared"
shared_native=C:/Users/xuzhi/Documents/gcc_knc/.work/_shared
export PATH="$drive/Program Files/Git/cmd:$shared/toolchain/cygwin/bin:$PATH"
export PYTHONDONTWRITEBYTECODE=1 OMP_DYNAMIC=FALSE OMP_NUM_THREADS=4
source config/release.env
variant=${1:?release or batch}; target=${2:-x86}
case $variant in release|batch) ;; *) exit 2;; esac
base=build/s10/df-batch;out="$base/$target-$variant";common="$base/$target-release"
mkdir -p "$out"
python scripts/s10-df-batch.py prepare "$variant"
special=0;vector=0;batch=0
[[ $variant == release ]] || { special=1;vector=1;batch=1; }
opts=(TARGET="$target" OUT="../$out" COMMON_OUT="../$common" DF_SPECIAL="$special" DF_VECTOR8="$vector"
      DF_BATCH="$batch" DF_VECTOR8_SCALAR_LOG_ATAN=1 DF_VECTOR8_GUARD=1 DF_VECTOR8_MARGIN=6.7163549441806109e-08
      DFS_TREE="../$base/$variant-tree" DFS_CAPTURE="../$base/$variant-capture.c" DFS_FLAGS=-fstack-usage)
# Release cannot enable a vector-only guard.
[[ $variant != release ]] || opts+=(DF_VECTOR8_GUARD=0)
if [[ $variant == release ]]; then
    make -C mk -f ../tests/s10-df-batch.mk -j2 "${opts[@]}" program > "$out/build.log" 2>&1
fi
make -C mk -f ../tests/s10-df-batch.mk -j2 "${opts[@]}" dfs-app > "$out/generator-build.log" 2>&1
if [[ $target == x86 ]]; then
    make -C mk -f ../tests/s10-df-batch.mk -j2 "${opts[@]}" dfs-capture > "$out/capture-build.log" 2>&1
    if [[ $variant == batch ]]; then
        make -C mk -f ../tests/s10-df-batch.mk -j2 "${opts[@]}" dfb-kernel > "$out/kernel-build.log" 2>&1
        "$out/batch-kernel.exe" > "$base/kernel.json"
    fi
else
    python C:/Users/xuzhi/Documents/gcc_knc/tools/knc_lint "$out/milkyway_nbody.mic" > "$out/knc-lint.txt" 2>&1
    echo 'PASS: knc_lint exit 0' >> "$out/knc-lint.txt"
    if [[ $variant == batch ]]; then
        make -C mk -f ../tests/s10-df-batch.mk -j2 "${opts[@]}" dfs-twin > "$out/twin-build.log" 2>&1
        "$shared_native/gcc-knc-16.2.0/bin/k1om-mpss-linux-gcc.exe" -O2 -march=knc -mveclibabi=knc -fno-math-errno -ffp-contract=off \
            -fopt-info-vec-missed="$base/compiler-items.txt" -S probes/s10_df_vector8_repro.c -o "$base/compiler-items.s"
        "$shared_native/toolchain/cross/bin/k1om-mpss-linux-objdump.exe" -dr "$out/milkyway_nbody.mic" > "$out/disassembly.txt"
    fi
    mkdir -p "$base/runtimes"
    for runtime in libgomp.so.1 libstdc++.so.6 libgcc_s.so.1; do
        cp -L "$shared_native/gcc-knc-16.2.0/k1om-mpss-linux/lib64/$runtime" "$base/runtimes/"
    done
fi
echo "Built $target-$variant"
