#!/usr/bin/env bash
# Long host runs; no card access and no downloads.
set -euo pipefail
cd "$(dirname "$0")/../.."
mkdir -p build/tmp
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
export PATH="$(cygpath -u C:/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin):$PATH"
export PYTHONDONTWRITEBYTECODE=1
make -C mk -j4 TARGET=x86 VECTOR_GRAVITY=0 program > build/s6-x86-build.log 2>&1
make -C mk -j4 TARGET=x86 OUT=../build/vector/x86-on VECTOR_GRAVITY=1 program > build/s6-x86-on-build.log 2>&1
python twin/vector/prepare_replay.py "${1:-../S1-06/twin/multicore}"
for variant in off on; do
    flag=0; [[ $variant != on ]] || flag=1
    make -C mk -f ../twin/vector.mk TARGET=x86 OUT=../build/vector/x86-$variant VECTOR_GRAVITY=$flag vector-replay > build/s6-replay-$variant-build.log 2>&1
    output=twin/vector/actual.bin
    [[ $variant != off ]] || output=twin/vector/actual-off.bin
    build/vector/x86-$variant/replay.exe "$output"
    cmp "$output" twin/vector/capture/expected.bin
done
python tests/vector_gravity_matrix.py | tee build/s6-exactness.log
python twin/vector/audit_range.py > build/s6-range.log
"$BASH" scripts/build-vector-gravity.sh
TWIN_HOME=${TWIN_HOME:-C:/Users/xuzhi/.claude/skills/knc-twin}
OBJDUMP=C:/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cross/bin/k1om-mpss-linux-objdump
python "$TWIN_HOME/scripts/knc_twin.py" capabilities --out build/s6-capabilities --force
python twin/vector/check_capabilities.py
"$OBJDUMP" -dr build/vector/card-on/milkyway_nbody.mic > twin/vector/card-on.disassembly.txt
python "$TWIN_HOME/scripts/from_binary.py" build/vector/card-on/milkyway_nbody.mic --function nbGravity8 --disassembly twin/vector/card-on.disassembly.txt --out twin/vector/vector-full.json --report twin/vector/conversion.json
cp twin/vector/vector-full.json twin/vector/vector-current.json
python - <<'PY_EXTRACT'
from pathlib import Path
s=Path('twin/vector/card-on.disassembly.txt').read_text()
a=s.index('<nbGravity8>:');b=s.find(chr(10)+chr(10),a)
Path('twin/vector/nbGravity8.disassembly.txt').write_text(s[a:b]+chr(10))
PY_EXTRACT
python - <<'PY_VEC'
from pathlib import Path
lines = [line.rstrip() for line in Path('build/s6-card-on-build.log').read_text().splitlines()
         if 'nbody_grav.c:' in line]
if lines:
    Path('twin/vector/vectorizer.txt').write_bytes((chr(10).join(lines)+chr(10)).encode())
PY_VEC
if [[ ${TWIN_SCALAR_READY:-0} == 1 ]]; then
    make -C mk -f ../twin/chunk.mk TARGET=card OUT=../build/vector/card-off VECTOR_GRAVITY=0 chunk-driver > build/s6-chunk-build.log 2>&1
    "$OBJDUMP" -dr build/gravity_chunk.mic > twin/vector/chunk.disassembly.txt
    python "$TWIN_HOME/scripts/from_binary.py" build/gravity_chunk.mic --function nbGravityChunk --with-callee nbGravity --disassembly twin/vector/chunk.disassembly.txt --out twin/vector/scalar-full.json
fi
python twin/vector/prepare_kernels.py
set +e
"$BASH" twin/vector/run.sh | tee twin/vector/run.log
twin_status=${PIPESTATUS[0]}
set -e
printf 'Twin exit status: %s (raw statuses retained in evidence)\n' "$twin_status"
python twin/vector/trace_utilization.py
python twin/vector/write_report.py
python tests/test_vector_gravity.py -v
