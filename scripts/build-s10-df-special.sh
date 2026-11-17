#!/usr/bin/env bash
# Release options, one baseline object set per target; at most two compiler jobs.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/tmp build/s10/df-special
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
shared=/c/Users/xuzhi/Documents/gcc_knc/.work/_shared
export PATH="/c/Program Files/Git/cmd:$shared/toolchain/cygwin/bin:$PATH"
export PYTHONDONTWRITEBYTECODE=1 OMP_DYNAMIC=FALSE OMP_NUM_THREADS=12
source config/release.env
variant=${1:?release, special or vmath}; target=${2:-x86}
case $variant in release|special|vmath) ;; *) exit 2;; esac
base=build/s10/df-special
out="$base/$target-$variant"
common="$base/$target-release"
mkdir -p "$out"
special=0; vmath=0
[[ $variant == release ]] || special=1
[[ $variant != vmath ]] || vmath=1
if [[ $variant == release ]]; then
    make -C mk -j2 TARGET="$target" OUT="../$out" program > "$out/build.log" 2>&1
fi
python scripts/s10-df-special.py prepare "$variant"
tree="$base/$variant-tree"
flags=; libs=
if [[ $vmath == 1 ]]; then
    if [[ $target == card ]]; then
        flags='-mveclibabi=knc -fno-math-errno'
        libs=-lknc_vmath
    else
        libs="$shared/S10-02/host/libknc_vmath.a"
    fi
fi
opts=(TARGET="$target" OUT="../$out" COMMON_OUT="../$common"
      DF_SPECIAL="$special" DF_VMATH="$vmath" DFS_TREE="../$tree"
      DFS_FLAGS="$flags" DFS_LIBS="$libs" DFS_CAPTURE="../$base/$variant-capture.c")
# Record the experiment library and extra flags in .build-options too.
make -C mk -f ../tests/s10-df-special.mk -j2 "${opts[@]}" dfs-app > "$out/generator-build.log" 2>&1
if [[ $target == x86 ]]; then
    make -C mk -f ../tests/s10-df-special.mk -j2 "${opts[@]}" \
        dfs-capture > "$out/capture-build.log" 2>&1
    if [[ $variant != release ]]; then
        make -C mk -f ../tests/s10-df-special.mk -j2 "${opts[@]}" dfs-kernel > "$out/kernel-build.log" 2>&1
        kernel=kernel.json
        [[ $variant != vmath ]] || kernel=vmath-kernel.json
        "$out/kernel.exe" > "$base/$kernel"
    fi
else
    python C:/Users/xuzhi/Documents/gcc_knc/tools/knc_lint "$out/milkyway_nbody.mic" > "$out/knc-lint.txt" 2>&1
    echo 'PASS: knc_lint exit 0' >> "$out/knc-lint.txt"
    cp "$out/vec-missed.txt" "$base/card-$variant-vec.txt"
    mkdir -p "$base/runtimes"
    for runtime in libgomp.so.1 libstdc++.so.6 libgcc_s.so.1; do
        cp -L "$shared/gcc-knc-16.2.0/k1om-mpss-linux/lib64/$runtime" "$base/runtimes/"
    done
fi
echo "Built $target-$variant"
