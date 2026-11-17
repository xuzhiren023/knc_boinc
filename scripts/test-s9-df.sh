#!/usr/bin/env bash
# Offline reproduction. Each core timing variant runs once; full generation is opt-in.
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/s9-df-common.sh
if [[ ${1:-} == --full && -f build/s9/df/full-started.json ]]; then
    echo 'Full generation already launched in this worktree; inspect retained proof.' >&2
    exit 1
fi
bash scripts/build-s9-df.sh x86-dfbase x86 0 0
bash scripts/build-s9-df.sh x86-dfreuse x86 1 0
python scripts/s9-df.py core > build/s9/df/core-proof.log 2>&1
bash scripts/build-s9-df.sh x86-dfvector x86 1 1
make -C mk -f ../tests/s9-df.mk -j2 TARGET=x86 OUT=../build/s9/x86-dfvector \
    TREE_VARIANT=2 PARALLEL_QUAD=1 STATIC_INTEGRATE=1 PHASE_TIMERS=1 \
    VECTOR_GRAVITY=0 FORCE_CHUNK=4 WALK_LAYOUT=0 TREE_IDENTITY=0 WALK_COUNTERS=0 \
    OPTFLAGS=-O2 DF_REUSE=1 DF_VECTOR=1 DF_STATS=1 \
    DF_SOURCE=../build/s9/df/experiment-tree/nbody/src/nbody_mixeddwarf.c \
    df-kernel > build/s9/df/kernel-build.log 2>&1
build/s9/x86-dfvector/kernel.exe > build/s9/df/kernel.txt 2>&1
python scripts/s9-df.py vector > build/s9/df/vector-proof.log 2>&1
bash scripts/build-s9-df.sh card-dfreuse card 1 0
if python -c 'import json; import sys; sys.exit(not json.load(open("build/s9/df/vector-proof.json"))["kept"])'; then
    bash scripts/build-s9-df.sh card-dfvec card 1 1
fi
# A final exact-reuse correctness capture also ensures its TU is restored after
# the shared generated capture source was used for the isolated experiment.
bash scripts/build-s9-df.sh x86-dfreuse x86 1 0
python scripts/s9-df.py verify_final > build/s9/df/final-core-proof.log 2>&1
python scripts/s9-df.py stage > build/s9/df/card-commands.txt
if [[ ${1:-} == --full ]]; then
    # The driver refuses a second full launch in the same worktree.
    python scripts/s9-df.py full > build/s9/df/full-proof.log 2>&1
fi
python tests/test_s9_df.py
