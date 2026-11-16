#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/tmp
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
export PATH="/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin:$PATH"
python twin/prepare_capture.py --multicore
sed 's/capture_multicore.h/x87_capture.h/' build/capture_grav.c > build/x87_grav.c
make -C mk -f ../twin/host.mk x87-host > build/s1-07-x87-build.log 2>&1
export OMP_NUM_THREADS=1 OMP_DYNAMIC=FALSE
build/x87_gravity.exe -f workunits/large/params.lua -h workunits/large/input.hist \
    --seed 670828913 --nthreads 1 --ignore-checkpoint --checkpoint-interval=-1 \
    -c build/s1-07-x87.checkpoint 20000
