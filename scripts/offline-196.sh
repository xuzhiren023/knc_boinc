#!/usr/bin/env bash
# S7-01 full offline regression. Sources are fetched only by fetch.sh.
set -euo pipefail
cd "$(dirname "$0")/.."
task_bash=$BASH
export PATH="/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin:$PATH"
mkdir -p build/tmp
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
export MAKEFLAGS="${MAKEFLAGS:--j6}"
# Git for Windows understands this native worktree's ownership/path metadata.
task_git='/c/Program Files/Git/cmd'
PATH="$task_git:$PATH" "$task_bash" scripts/fetch.sh
make -C mk x86 card
"$task_bash" tests/boinc-api.sh
"$task_bash" tests/wrapper.sh
"$task_bash" tests/graphics.sh
PATH="$task_git:$PATH" "$task_bash" tests/force-chunk.sh
python tests/test_packaging.py
python tests/nbody_196_matrix.py
"$task_bash" scripts/build-vector-gravity.sh
# The card-command regression also prints the existing libm probe handoff.
make -C mk -f ../probes/probe.mk TARGET=card libm-probe
cp build/card/libm_probe.mic dist/card/
PATH="$task_git:$PATH" python -m unittest discover -s tests -v
"$task_bash" scripts/card-check.sh > build/card-commands.txt
printf 'PASS full offline N-body 1.96 regression; card commands were printed only.\n'
