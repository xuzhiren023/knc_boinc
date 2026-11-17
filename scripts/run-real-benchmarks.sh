#!/usr/bin/env bash
# Run only on an otherwise idle laptop. No sweeps and no concurrent jobs.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/tmp build/real-benchmarks
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
export PATH="/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin:$PATH"
source config/release.env
export GEN_PIPELINE=0 GEN_PROFILE=0 WALK_PREFETCH=0 WALK_HOT=0 WALK_SCHEDULE=0 WALK_PROFILE=0 WALK_PROOF=0
make -C mk -j2 TARGET=x86 OUT=../build/real-benchmarks/x86-release-timers PHASE_TIMERS=1 program \
    > build/real-benchmarks/build.log 2>&1
for case in core-small real-steps; do
    for variant in release stock; do
        python scripts/real-benchmarks.py "$case" "$variant"
    done
done
# The runner refuses an existing run directory, including an interrupted run.
python scripts/real-benchmarks.py 117676 release
