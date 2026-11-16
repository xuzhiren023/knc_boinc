#!/usr/bin/env bash
# Full acceptance: fetch/build, unit test, four science runs, timing/identity.
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin:$PATH"
mkdir -p build/tmp
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
bash scripts/fetch.sh && make -C mk x86
python -m unittest discover tests
bash scripts/run_x86.sh
python - <<'PY'
from pathlib import Path
import re

root = Path('runs/x86')
for case in ('small', 'medium'):
    a, b = (root / (case + '-' + str(n)) for n in (1, 4))
    seconds = float((a / 'seconds.txt').read_text().strip())
    assert (seconds < 30 if case == 'small' else 120 <= seconds <= 600), (case, seconds)
    def science(path):
        output = (path / 'stdout.txt').read_text() + (path / 'stderr.txt').read_text()
        likelihood = re.findall(r'<search_likelihood>([^<]+)</search_likelihood>', output)
        histogram = [line.strip() for line in (path / 'histogram.txt').read_text().splitlines()
                     if line.strip() and not line.startswith('#')]
        return likelihood, histogram
    identical = science(a) == science(b)
    print('{}: scientific output bit-identical at 1/4 threads: {}'.format(case, identical))
PY
