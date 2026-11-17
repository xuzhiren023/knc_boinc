#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/tmp build/s10/df-vector8
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
shared=/c/Users/xuzhi/Documents/gcc_knc/.work/_shared
export PATH="$shared/toolchain/cygwin/bin:$PATH"
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=4
cc="$shared/gcc-knc-16.2.0/bin/k1om-mpss-linux-gcc"
od="$shared/toolchain/cross/bin/k1om-mpss-linux-objdump"
base=build/s10/df-vector8
"$cc" -O2 -march=knc -mveclibabi=knc -fno-math-errno -ffp-contract=off \
    -fopt-info-vec-missed="$base/compiler-items.txt" \
    -S probes/s10_df_vector8_repro.c -o "$base/compiler-items.s"
if "$cc" -O2 -march=knc -DREPRO_AGGREGATE_ABI -S probes/s10_df_vector8_repro.c \
    -o "$base/compiler-aggregate.s" > "$base/compiler-aggregate.txt" 2>&1; then
    echo 'Aggregate ABI repro now compiles' >> "$base/compiler-aggregate.txt"
else
    echo 'Retained expected aggregate-return compiler diagnostic' >> "$base/compiler-aggregate.txt"
fi
for variant in release vector8 guard scalar scalar-guard; do
    "$od" -dr "$base/card-$variant/milkyway_nbody.mic" > "$base/card-$variant/disassembly.txt"
done
python - <<'PY'
from pathlib import Path
import hashlib, json, subprocess, time
b = Path('build/s10/df-vector8')
skill = Path('C:/Users/xuzhi/.claude/skills/knc-twin')
shared = Path('C:/Users/xuzhi/Documents/gcc_knc/.work/_shared')
rows = []
def run(args, log):
    t=time.monotonic()
    with (b/log).open('w') as f:
        p=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT)
    rows.append(dict(command=args, exit_code=p.returncode, host_seconds=time.monotonic()-t))
run(['python',str(skill/'scripts/knc_twin.py'),'capabilities','--out',str(b/'twin-capabilities')], 'twin-capabilities.txt')
cap=json.loads((b/'twin-capabilities/capabilities.json').read_text())
# Inspect the actual capabilities before attempting the faithful binary adapter.
print(json.dumps(cap,indent=2)[:12000])
for variant in ['release','vector8']:
    out=b/('twin-'+variant); out.mkdir(exist_ok=True)
    run(['python',str(skill/'scripts/from_binary.py'),str(b/('card-'+variant)/'milkyway_nbody.mic'),
         '--function','gauss_quad._omp_fn.0','--disassembly',str(b/('card-'+variant)/'disassembly.txt'),
         '--out',str(out/'kernel.json'),'--report',str(out/'adapter.json')], 'twin-'+variant+'.txt')
(b/'twin-effort.json').write_text(json.dumps(dict(commands=rows, host_seconds=sum(r['host_seconds'] for r in rows),
    model_table_used=False, simulations_run=0),indent=2)+'\n')
files=[shared/'gcc-knc-16.2.0/lib/gcc/k1om-mpss-linux/16.2.0/libknc_vmath.a',
       shared/'S10-02/knc/libknc_vmath.a',shared/'S10-02/host/libknc_vmath.a']
hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
assert hashes[str(files[0])]==hashes[str(files[1])]=='fc732e6f48b7a4bae49eeb32fe9fd78f730e10597b83cfe0495aca150fc4f786'
(b/'library-provenance.json').write_text(json.dumps(hashes,indent=2)+'\n')
PY
python scripts/twin-s10-df-vector8.py
python scripts/twin-s10-df-vector8.py scalar
