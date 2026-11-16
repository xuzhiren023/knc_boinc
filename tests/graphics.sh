#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin:$PATH"
mkdir -p build/tmp build/graphics
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
make -C mk -j6 graphics graphics-test x86
build/graphics/format.exe
rm -f build/graphics/window.bmp build/graphics/final-state.txt build/graphics/demo.snapshot
# Full medium evolution: tidal stripping, not the former tiny initial clump.
cp workunits/medium/params.lua build/graphics/demo.lua
OMP_NUM_THREADS=4 build/x86/milkyway_nbody.exe -f build/graphics/demo.lua -h workunits/medium/input.hist -z build/graphics/histogram.txt -o build/graphics/final-state.txt -c build/graphics/checkpoint --seed 670828913 --nthreads 4 --ignore-checkpoint --checkpoint-interval=-1 1024 > build/graphics/science-stdout.txt 2> build/graphics/science-stderr.txt
python tools/make_demo_snapshot.py build/graphics/final-state.txt build/graphics/demo.snapshot --time 3.945
build/graphics/graphics_test.exe
python tests/test_graphics.py
