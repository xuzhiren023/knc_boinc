#!/bin/sh
# Lead-only native smoke run: stage with the app/runtimes and chosen Lua/histogram.
# Usage: sh card-snapshot-run.sh THREADS [normal nbody arguments...]
set -eu
threads=$1
shift
export OMP_NUM_THREADS="$threads" OMP_DYNAMIC=FALSE KNC_WRAPPER_FILES=1
./milkyway_nbody.mic --snapshot-interval 5 --nthreads "$threads" "$@"
test -s snapshot
printf 'Snapshot header (magic, version, size, sampled bodies):\n'
od -An -tu4 -N16 snapshot
