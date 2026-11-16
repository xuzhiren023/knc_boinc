#!/usr/bin/env bash
# Rebuild app first; record a separate host-only snapshot from the pinned large case.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/tmp twin/multicore/capture
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
export PATH="/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin:$PATH"
export PYTHONDONTWRITEBYTECODE=1
make -C mk -j4 card > build/s1-06-card.log 2>&1
make -C mk -j4 x86 > build/s1-06-x86.log 2>&1
python twin/prepare_capture.py --multicore
make -C mk -f ../twin/host.mk capture-host > build/s1-06-capture-build.log 2>&1
for target in x86 card; do
    make -C mk -f ../twin/host.mk capture-layout TARGET="$target" >> build/s1-06-layout.log 2>&1
done
objcopy -O binary -j .data build/layout-x86.o twin/multicore/capture/layout-x86.bin
C:/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cross/bin/k1om-mpss-linux-objcopy \
    -O binary -j .data build/layout-card.o twin/multicore/capture/layout-card.bin
# capture_log.c retains its original fixed output path. Preserve S1-03/S1-05 bytes.
cp twin/capture/log-input.bin build/s1-06-saved-log-input.bin
cp twin/capture/log-expected.bin build/s1-06-saved-log-expected.bin
cp twin/capture/host-fcw.bin build/s1-06-saved-host-fcw.bin
restore_logs() {
    cp build/s1-06-saved-log-input.bin twin/capture/log-input.bin
    cp build/s1-06-saved-log-expected.bin twin/capture/log-expected.bin
    cp build/s1-06-saved-host-fcw.bin twin/capture/host-fcw.bin
}
trap restore_logs EXIT
export OMP_NUM_THREADS=1 OMP_DYNAMIC=FALSE
set +e
build/capture.exe -f workunits/large/params.lua -h workunits/large/input.hist \
    --seed 670828913 --nthreads 1 --print-histogram --ignore-checkpoint \
    --checkpoint-interval=-1 -z build/s1-06-capture.hist -c build/s1-06-capture.checkpoint \
    20000 > build/s1-06-capture-stdout.txt 2> build/s1-06-capture-stderr.txt
status=$?
set -e
echo "$status" > build/s1-06-capture-exit.txt
[[ "$status" == 0 ]]
python twin/check_multicore_capture.py
