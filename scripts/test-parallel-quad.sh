#!/usr/bin/env bash
# Offline S8-03 matrix; no downloads or card access. Run under Git Bash.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/tmp build/s8
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
# Keep Windows Python and Git for source/evidence tooling; use explicit Cygwin
# make/compiler paths, as required by the repository's native build.
cyg=/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin
export PATH="/c/Program Files/Git/cmd:$cyg:$PATH"
export PYTHONDONTWRITEBYTECODE=1
python tests/quad-kernel.py
python tests/prepare_quad_capture.py
for variant in off on; do
    flag=0
    [[ $variant != on ]] || flag=1
    make -C mk -f ../tests/quad.mk -j4 TARGET=x86 \
        OUT=../build/s8/x86-$variant PARALLEL_QUAD=$flag \
        VECTOR_GRAVITY=0 FORCE_CHUNK=4 \
        CAPTURE_SOURCE=../build/s8/mixeddwarf-$variant.c program \
        > build/s8/x86-$variant-build.log 2>&1
done
export OMP_DYNAMIC=FALSE
args=(4.90652 1 0.386382 0.20556 1.74668 0.0420765 46.125 15.623 -215.279 114.242 181.825 353270 1.21041 2.87629)
for spec in off:12 on:1 on:4 on:12; do
    IFS=: read -r variant threads <<< "$spec"
    out="runs/s8-quad/$variant-$threads"
    mkdir -p "$out"
    rm -f "$out/histogram.txt" "$out/initial-bodies.bin" "$out/exit.txt"
    export OMP_NUM_THREADS="$threads"
    export S8_INITIAL_BODIES="$(cygpath -am "$out/initial-bodies.bin")"
    command=(build/s8/x86-$variant/milkyway_nbody.exe
        -f workunits/core-small/params.lua
        -h workunits/core-small/OCS_data_2025_north_194.hist
        -z "$out/histogram.txt" -c "$out/checkpoint"
        --seed 65477096 --nthreads "$threads"
        --print-histogram --ignore-checkpoint --checkpoint-interval=-1
        -np 14 -p "${args[@]}")
    printf '%q ' "${command[@]}" > "$out/command.txt"
    echo >> "$out/command.txt"
    echo "Running core-small $variant/$threads"
    TIMEFORMAT='%3R'
    set +e
    { time "${command[@]}" > "$out/stdout.txt" 2> "$out/stderr.txt"; } 2> "$out/seconds.txt"
    status=$?
    set -e
    echo "$status" > "$out/exit.txt"
    [[ $status == 0 ]] || { cat "$out/stderr.txt" >&2; exit "$status"; }
    python scripts/compare.py "$out" "$out"
    grep 'S8_' "$out/stderr.txt"
    echo "Total $(cat "$out/seconds.txt") s"
done
python tests/test_parallel_quad.py
