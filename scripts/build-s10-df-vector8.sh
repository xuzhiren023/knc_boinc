#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/tmp build/s10/df-vector8
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
shared=/c/Users/xuzhi/Documents/gcc_knc/.work/_shared
export PATH="/c/Program Files/Git/cmd:$shared/toolchain/cygwin/bin:$PATH"
export PYTHONDONTWRITEBYTECODE=1 OMP_DYNAMIC=FALSE OMP_NUM_THREADS=4
source config/release.env
variant=${1:?release, vector8, guard, scalar or scalar-guard}; target=${2:-x86}
case $variant in release|vector8|guard|scalar|scalar-guard) ;; *) exit 2;; esac
base=build/s10/df-vector8
out="$base/$target-$variant"; common="$base/$target-release"
mkdir -p "$out"
special=0; vector=0; guard=0; scalar=0; margin=0.001
[[ $variant == release ]] || { special=1; vector=1; }
case $variant in guard|scalar-guard) guard=1;; esac
case $variant in scalar|scalar-guard) scalar=1;; esac
calibration=calibration.json
[[ $scalar == 0 ]] || calibration=calibration-scalar.json
if [[ $guard == 1 && -f $base/$calibration ]]; then
    margin=$(python -c 'import json,sys;print(json.load(open(sys.argv[1]))["margin"])' "$base/$calibration")
fi
if [[ $variant == release ]]; then
    make -C mk -j2 TARGET="$target" OUT="../$out" DF_VECTOR8_MARGIN="$margin" program > "$out/build.log" 2>&1
fi
python scripts/s10-df-vector8.py prepare "$variant"
tree="$base/$variant-tree"
opts=(TARGET="$target" OUT="../$out" COMMON_OUT="../$common"
      DF_SPECIAL="$special" DF_VECTOR8="$vector" DF_VECTOR8_GUARD="$guard"
      DF_VECTOR8_SCALAR_LOG_ATAN="$scalar"
      DF_VECTOR8_MARGIN="$margin" DFS_TREE="../$tree" DFS_CAPTURE="../$base/$variant-capture.c")
make -C mk -f ../tests/s10-df-vector8.mk -j2 "${opts[@]}" dfs-app > "$out/generator-build.log" 2>&1
if [[ $target == x86 ]]; then
    make -C mk -f ../tests/s10-df-vector8.mk -j2 "${opts[@]}" dfs-capture > "$out/capture-build.log" 2>&1
    if [[ $variant == vector8 || $variant == scalar ]]; then
        make -C mk -f ../tests/s10-df-vector8.mk -j2 "${opts[@]}" dfs-kernel > "$out/kernel-build.log" 2>&1
        kernel=kernel.json
        [[ $scalar == 0 ]] || kernel=kernel-scalar.json
        "$out/kernel.exe" > "$base/$kernel"
        python scripts/s10-df-vector8.py calibrate "$variant"
    fi
else
    if [[ $variant == vector8 || $variant == scalar ]]; then
        make -C mk -f ../tests/s10-df-vector8.mk -j2 "${opts[@]}" dfs-twin > "$out/twin-build.log" 2>&1
        python C:/Users/xuzhi/Documents/gcc_knc/tools/knc_lint "$out/twin-kernel.mic" > "$out/twin-knc-lint.txt" 2>&1
    fi
    python C:/Users/xuzhi/Documents/gcc_knc/tools/knc_lint "$out/milkyway_nbody.mic" > "$out/knc-lint.txt" 2>&1
    echo 'PASS: knc_lint exit 0' >> "$out/knc-lint.txt"
    mkdir -p "$base/runtimes"
    for runtime in libgomp.so.1 libstdc++.so.6 libgcc_s.so.1; do
        cp -L "C:/Users/xuzhi/Documents/gcc_knc/.work/_shared/gcc-knc-16.2.0/k1om-mpss-linux/lib64/$runtime" "$base/runtimes/"
    done
fi
echo "Built $target-$variant"
