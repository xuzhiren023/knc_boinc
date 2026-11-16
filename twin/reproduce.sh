#!/usr/bin/env bash
# End-to-end host-only evidence. No card execution and no downloads except pinned fetch.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/tmp twin/capture twin/profile
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
export PATH="/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin:$PATH"
bash scripts/fetch.sh > build/fetch-offline.log 2>&1
make -C mk -j4 card > build/card-build.log 2>&1
make -C mk -j4 x86 > build/x86-build.log 2>&1
bash scripts/run_x86.sh 'small medium large' > build/x86-references.log 2>&1
make -C mk -f ../twin/host.mk -j4 profile-host OUT=../build/profile \
 COMMON_CFLAGS='-O2 -g -pg -fopenmp -fno-strict-aliasing -ffp-contract=off' \
 COMMON_LDFLAGS='-pg -fopenmp' > build/profile-build.log 2>&1
export OMP_NUM_THREADS=1 OMP_DYNAMIC=FALSE
args=(-f workunits/small/params.lua -h workunits/small/input.hist --seed 670828913 \
 --nthreads 1 --print-histogram --ignore-checkpoint --checkpoint-interval=-1)
build/profile/milkyway_nbody.exe "${args[@]}" -z twin/profile/histogram.txt \
 -c build/profile/checkpoint 64 > twin/profile/stdout.txt 2> twin/profile/stderr.txt
mv gmon.out twin/profile/gmon.out
gprof build/profile/milkyway_nbody.exe twin/profile/gmon.out > twin/profile/gprof.txt
python twin/prepare_capture.py
make -C mk -f ../twin/host.mk capture-host > build/capture-build.log 2>&1
for target in x86 card; do
 make -C mk -f ../twin/host.mk capture-layout TARGET="$target" >> build/layout.log 2>&1
done
objcopy -O binary -j .data build/layout-x86.o twin/capture/layout-x86.bin
C:/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cross/bin/k1om-mpss-linux-objcopy \
 -O binary -j .data build/layout-card.o twin/capture/layout-card.bin
build/capture.exe "${args[@]}" -z build/capture.hist -c build/capture.checkpoint 64 \
 > build/capture-stdout.txt 2> build/capture-stderr.txt
mkdir -p runs/x86/capture-small-1
cp build/capture.hist runs/x86/capture-small-1/histogram.txt
cp build/capture-stdout.txt runs/x86/capture-small-1/stdout.txt
cp build/capture-stderr.txt runs/x86/capture-small-1/stderr.txt
printf '0' > runs/x86/capture-small-1/exit.txt
printf '0' > twin/profile/exit.txt
python scripts/compare.py runs/x86/small-1 runs/x86/capture-small-1 > build/capture-reference-compare.txt
python scripts/compare.py runs/x86/small-1 twin/profile > build/profile-reference-compare.txt
python twin/capture_manifest.py
# Nonzero twin exit codes are findings, retained in logs and per-command JSON.
set +e
bash twin/run.sh > twin/run.log 2>&1
gravity=$?
bash twin/run_hot.sh > twin/hot-run.log 2>&1
hot=$?
set -e
printf 'gravity twin exit=%s; measured hotspot twin exit=%s\n' "$gravity" "$hot"
bash scripts/card-check.sh > dist/card/lead-commands.sh
python twin/write_report.py
python tests/test_twin.py
