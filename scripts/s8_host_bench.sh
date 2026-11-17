#!/usr/bin/env bash
# IEEE host competitors: native scalar and eight-body vector force, same source.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/tmp build/s8-09
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
export PATH="/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin:$PATH"
export PYTHONDONTWRITEBYTECODE=1
source config/s8-09.env
export OPTFLAGS=${HOST_OPTFLAGS:--O3 -march=native -mtune=native -mno-avx -mno-avx2 -mno-avx512f -mno-fma}
make -C mk -j2 TARGET=x86 OUT=../build/s8-09/x86-native program > build/s8-09/native-build.log 2>&1
make -C mk -f ../tests/s8-capture.mk TARGET=x86 OUT=../build/s8-09/x86-native s8-vector-bench > build/s8-09/native-vector-build.log 2>&1
python - <<'PY'
import hashlib
import importlib.util
import json
import os
from pathlib import Path
root = Path.cwd()
spec = importlib.util.spec_from_file_location('s8', root/'scripts/s8_integration.py')
s8 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s8)
records = {}
for label, name in [('native-sse-scalar', 'milkyway_nbody.exe'), ('native-sse-vector', 'vector-bench.exe')]:
    binary = s8.BUILD/'x86-native'/name
    records[label] = dict(binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
                         flags=os.environ['OPTFLAGS']+' -ffp-contract=off', threads=12, cases={})
    for case in ('large', 'core-small'):
        out = s8.run(binary, case, 12, label+'-'+case)
        reference = s8.copy_reference(case)
        assert s8.compare.compare(reference, out, s8.compare.TOLERANCE) == 0
        assert s8.compare.load_run(reference)[0].hex() == s8.compare.load_run(out)[0].hex()
        records[label]['cases'][case] = dict(seconds=float((out/'seconds.txt').read_text()),
                                            run=str(out.relative_to(root)), bit_identical=True)
(s8.BUILD/'host-competitors.json').write_text(json.dumps(records, indent=2)+'\n')
PY
