#!/usr/bin/env bash
# No model modifications, profile overlays, instruction edits or oracle relaxation.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/tmp
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
export PATH="/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin:$PATH"
export PYTHONDONTWRITEBYTECODE=1
TWIN_HOME=${TWIN_HOME:-C:/Users/xuzhi/.claude/skills/knc-twin}
OBJDUMP=C:/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cross/bin/k1om-mpss-linux-objdump.exe
make -C mk -f ../twin/chunk.mk TARGET=card chunk-driver > build/s1-07-chunk-build.log 2>&1
"$OBJDUMP" -dr build/gravity_chunk.mic > twin/chunk.disassembly.txt
python "$TWIN_HOME/scripts/from_binary.py" build/gravity_chunk.mic --function nbGravityChunk \
    --with-callee nbGravity --disassembly twin/chunk.disassembly.txt \
    --out twin/multicore/chunk-full.json
python twin/prepare_chunks.py --bodies "${1:-128}"
seconds=${CHUNK_MAX_SECONDS:-1740}
[[ "$seconds" =~ ^[0-9]+$ ]] && (( seconds > 0 && seconds <= 1740 ))
failed=0
for name in baseline unit ring; do
    scale=unit
    [[ "$name" != ring ]] || scale=ring
    out="twin/multicore/chunk-$name"
    cmd=(python "$TWIN_HOME/scripts/knc_twin.py" simulate "$out.json" --scale "$scale"
        --profile card-7120-measured --max-steps 10000000 --max-seconds "$seconds"
        --no-issue-log --out "$out" --force)
    echo "\$ ${cmd[*]}"
    timeout 1790s "${cmd[@]}" || failed=1
done
for name in unit ring; do
    cmd=(python "$TWIN_HOME/scripts/knc_twin.py" compare twin/multicore/chunk-baseline/result.json
        "twin/multicore/chunk-$name/result.json" --out "twin/multicore/chunk-compare-$name" --force)
    echo "\$ ${cmd[*]}"
    "${cmd[@]}" || failed=1
done
exit "$failed"
