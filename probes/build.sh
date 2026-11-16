#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/tmp runs/probe runs/card dist/card
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
export PATH="/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin:$PATH"
for target in x86 card; do make -C mk -f ../probes/probe.mk TARGET="$target" -j4 libm-probe; done
cp build/card/libm_probe.mic dist/card/
build/x86/libm_probe.exe twin/capture/log-input.bin > runs/probe/x86.txt
bash scripts/probe-commands.sh > dist/card/probe-commands.sh
make -C mk -f ../probes/probe.mk TARGET=x86 fildl-host
build/x86/fildl_host.exe > twin/fildl-host.txt
python C:/Users/xuzhi/Documents/gcc_knc/tools/knc_lint dist/card/libm_probe.mic > dist/card/probe-knc-lint.txt 2>&1
python - <<'PY'
import hashlib,json
from pathlib import Path
files=[Path('build/card/libm_probe.mic'),Path('build/x86/libm_probe.exe'),Path('twin/capture/log-input.bin')]
files+=sorted(Path('build/card/crlibm').rglob('*.o'))+sorted(Path('build/x86/crlibm').rglob('*.o'))
m={'flags_source':'mk/sources.mk (same objects linked by application and probe)',
   'probe_rows':len(Path('runs/probe/x86.txt').read_text().splitlines()),
   'files':[{'path':p.as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]}
Path('twin/probe-manifest.json').write_text(json.dumps(m,indent=2)+'\n')
PY
printf '%s\n' 'PASS: knc_lint exit 0' >> dist/card/probe-knc-lint.txt
C:/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cross/bin/k1om-mpss-linux-nm \
 -u build/card/milkyway_nbody.mic > twin/app-undefined-symbols.txt
