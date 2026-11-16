#!/usr/bin/env bash
# Long host runs; does not run a card or fetch/download any source.
set -euo pipefail
cd "$(dirname "$0")/../.."
mkdir -p build/tmp
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
export PATH="/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin:$PATH"
export PYTHONDONTWRITEBYTECODE=1
make -C mk -j4 TARGET=x86 VECTOR_GRAVITY=0 program > build/s6-x86-build.log 2>&1
make -C mk -j4 TARGET=x86 OUT=../build/vector/x86-on VECTOR_GRAVITY=1 program > build/s6-x86-on-build.log 2>&1
# Optional first argument is a complete S1-06 capture directory (capture.json,
# capture-summary.json and capture/*.bin); default is the sibling S1-06 worktree.
python twin/vector/prepare_replay.py "${1:-../S1-06/twin/multicore}"
make -C mk -f ../twin/vector.mk TARGET=x86 OUT=../build/vector/x86-on VECTOR_GRAVITY=1 vector-replay > build/s6-replay-build.log 2>&1
build/vector/x86-on/replay.exe twin/vector/actual.bin
cmp twin/vector/actual.bin twin/vector/capture/expected.bin
python tests/vector_gravity_matrix.py | tee build/s6-exactness.log
python twin/vector/audit_range.py > build/s6-range.log
"$BASH" scripts/build-vector-gravity.sh
make -C mk -f ../twin/chunk.mk TARGET=card OUT=../build/vector/card-off VECTOR_GRAVITY=0 chunk-driver > build/s6-chunk-build.log 2>&1
TWIN_HOME=${TWIN_HOME:-C:/Users/xuzhi/.claude/skills/knc-twin}
OBJDUMP=C:/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cross/bin/k1om-mpss-linux-objdump
python "$TWIN_HOME/scripts/knc_twin.py" capabilities --out build/s6-capabilities --force
"$OBJDUMP" -dr build/vector/card-on/milkyway_nbody.mic > twin/vector/card-on.disassembly.txt
"$OBJDUMP" -dr build/gravity_chunk.mic > twin/vector/chunk.disassembly.txt
python "$TWIN_HOME/scripts/from_binary.py" build/vector/card-on/milkyway_nbody.mic --function nbGravity8 --disassembly twin/vector/card-on.disassembly.txt --out twin/vector/vector-full.json --report twin/vector/conversion.json
python "$TWIN_HOME/scripts/from_binary.py" build/gravity_chunk.mic --function nbGravityChunk --with-callee nbGravity --disassembly twin/vector/chunk.disassembly.txt --out twin/vector/scalar-full.json
cp twin/vector/vector-full.json twin/vector/vector-current.json
python - <<'PY_EXTRACT'
from pathlib import Path
s=Path('twin/vector/card-on.disassembly.txt').read_text()
a=s.index('<nbGravity8>:');b=s.find(chr(10)+chr(10),a)
Path('twin/vector/nbGravity8.disassembly.txt').write_text(s[a:b]+chr(10))
s=Path('third_party/milkywayathome_client/nbody/src/nbody_grav.c').read_text()
Path('build/vector/rejected-grav.c').write_text(s.replace('#pragma GCC novector','/* vector lowering probe */'))
PY_EXTRACT
make -C mk -f ../twin/vector.mk TARGET=card OUT=../build/vector/card-on VECTOR_GRAVITY=1 lowering-probe > build/s6-lowering.log 2>&1
"$OBJDUMP" -dr build/vector/rejected-grav.o > twin/vector/rejected-lowering.disassembly.txt
if grep 'nbody_grav.c:' build/s6-card-on-build.log > build/s6-vectorizer-new.txt; then
    cp build/s6-vectorizer-new.txt twin/vector/vectorizer.txt
fi
python twin/vector/prepare_kernels.py
set +e
"$BASH" twin/vector/run.sh | tee twin/vector/run.log
set -e
python twin/vector/trace_utilization.py
python twin/vector/write_report.py
python tests/test_vector_gravity.py # expected nonzero until blockers are resolved
