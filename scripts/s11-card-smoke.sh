#!/usr/bin/env bash
# Lead only: one core-small job using the rebuilt wrapper/package and real transport.
# Engineer validation is bash -n only; caller supplies the owner's config/key path.
set -euo pipefail
[[ $# == 1 ]] || { echo 'usage: s11-card-smoke.sh OWNER_CONFIG' >&2; exit 2; }
root=$(cd "$(dirname "$0")/.." && pwd)
cd "$root"
export PATH="/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin:$PATH"
mkdir -p build/tmp
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
export PYTHONDONTWRITEBYTECODE=1
config=$(cygpath -am "$(realpath "$1")")
slot="$root/build/s11/card-smoke"
if [[ -e "$slot/knc_remote" || -e "$slot/knc_turn" ]]; then
    echo 'Retained smoke lease/turn: inspect or resume with scripts/run_wrapper.sh first.' >&2
    exit 2
fi
mkdir -p "$slot"
cp "$config" "$slot/knc_wrapper.cfg"
cp workunits/core-small/params.lua "$slot/params.lua"
cp workunits/core-small/OCS_data_2025_north_194.hist "$slot/input.hist"
cat >> "$slot/knc_wrapper.cfg" <<CFG
package_dir=$(cygpath -am "$root/dist/milkyway_package")
app=milkyway_nbody.mic
card_booking=1
checkpoint_interval=120
CFG
bash scripts/run_wrapper.sh "$slot" -f params.lua -h input.hist -z histogram.txt \
    --ignore-checkpoint --seed 65477096 -np 14 -p \
    4.90652 1 0.386382 0.20556 1.74668 0.0420765 46.125 15.623 \
    -215.279 114.242 181.825 353270 1.21041 2.87629
python - "$slot/nbody_stderr.txt" <<'PY'
import re
import sys
from pathlib import Path
text = Path(sys.argv[1]).read_text()
value = re.search(r'<search_likelihood>\s*(.*?)\s*</search_likelihood>', text)[1]
assert value == '-2357.216400957532642', value
print('PASS card core-small likelihood; inspect knc_wrapper.log and shared ledger turn closure')
PY
