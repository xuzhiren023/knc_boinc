#!/bin/sh
# Lead-only native harness; groups of four actual siblings, no kernel changes.
set -eu
export OMP_NUM_THREADS=240 OMP_DYNAMIC=FALSE OMP_PROC_BIND=TRUE
unset OMP_PLACES
# card_run supplies an authorized 60-core CPU mask. Build affinity from sysfs,
# not assumptions about logical CPU numbering. Four adjacent OpenMP ids share
# a physical core; static,4 then gives that core neighbouring body chunks.
affinity=$(./walk-affinity.mic)
export GOMP_CPU_AFFINITY="$affinity"
printf 'WALK_AFFINITY %s\n' "$affinity"
: > stderr.txt
set +e
"$@"
status=$?
cp stderr.txt claude-stderr.txt
cat claude-stderr.txt >&2
exit "$status"
