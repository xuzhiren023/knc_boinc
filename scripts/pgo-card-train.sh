#!/bin/sh
# card_run's run directory is the working directory; profiles retain their hierarchy.
set -eu
export GCOV_PREFIX="$PWD/gcda"
. ./pgo-path.env
export OMP_NUM_THREADS=240 OMP_DYNAMIC=FALSE
./milkyway_nbody.mic "$@"
# --collect accepts regular claude-* files. Archive only after normal gcov flush.
tar -czf claude-profiles.tar.gz gcda
