#!/bin/sh
# Card-only harness. Retain BOINC's redirected diagnostics before runner cleanup.
set -u
export OMP_NUM_THREADS=240 OMP_DYNAMIC=FALSE
: > stderr.txt
./milkyway_nbody.mic "$@"
status=$?
cp stderr.txt claude-stderr.txt
cat claude-stderr.txt >&2
exit "$status"
