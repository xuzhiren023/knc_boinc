#!/usr/bin/env bash
# Full host acceptance: fetch/build, unit tests, six reference runs, identity.
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin:$PATH"
mkdir -p build/tmp
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
bash scripts/fetch.sh && make -C mk x86 card
python -m unittest discover tests
bash scripts/card-check.sh > build/card-commands.txt
bash scripts/run_x86.sh
bash scripts/run_x86.sh large "1 12"
python scripts/compare.py runs/x86/large-1 runs/x86/large-12
python - <<'PY'
from pathlib import Path
import re

root = Path('runs/x86')
for case in ('small', 'medium'):
    a, b = (root / (case + '-' + str(n)) for n in (1, 4))
    seconds = float((a / 'seconds.txt').read_text().strip())
    print(case, "single-thread wall seconds:", seconds)
    def science(path):
        output = (path / 'stdout.txt').read_text() + (path / 'stderr.txt').read_text()
        likelihood = re.findall(r'<search_likelihood>([^<]+)</search_likelihood>', output)
        histogram = [line.strip() for line in (path / 'histogram.txt').read_text().splitlines()
                     if line.strip() and not line.startswith('#')]
        return likelihood, histogram
    identical = science(a) == science(b)
    print('{}: scientific output bit-identical at 1/4 threads: {}'.format(case, identical))
PY
