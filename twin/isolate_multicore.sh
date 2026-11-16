#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/tmp
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
export PATH="/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin:$PATH"
export PYTHONDONTWRITEBYTECODE=1
TWIN_HOME=${TWIN_HOME:-C:/Users/xuzhi/.claude/skills/knc-twin}
OBJDUMP=C:/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cross/bin/k1om-mpss-linux-objdump.exe
# Apps and capture must already have been built with capture_multicore.sh.
python "$TWIN_HOME/scripts/knc_twin.py" capabilities --out build/s1-07-capabilities --force
"$OBJDUMP" -dr build/card/milkyway_nbody.mic > twin/card.disassembly.txt
python "$TWIN_HOME/scripts/from_binary.py" build/card/milkyway_nbody.mic --function nbGravity \
    --disassembly twin/card.disassembly.txt --init twin/capture.json --out twin/gravity-full.json
python twin/cut_gravity.py
python twin/prepare_multicore.py
gcc -O2 -mfpmath=387 twin/x87_oracle.c -o build/x87_oracle.exe
python twin/isolate_multicore.py
python "$TWIN_HOME/scripts/knc_twin.py" functional twin/x87-rounding-repro.json \
    --out twin/x87-rounding-repro --force
