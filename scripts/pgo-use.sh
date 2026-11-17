#!/usr/bin/env bash
# Lead: bash scripts/pgo-use.sh after both pgo-train.sh jobs have succeeded.
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/s9-common.sh
python scripts/s9-pgo.py import-card
python scripts/s9-pgo.py clean-merged
"$S9_SHARED/gcc-knc-16.2.0/bin/k1om-mpss-linux-gcov-tool" merge \
    build/s9/profiles/core-small build/s9/profiles/large -o build/s9/profiles/merged
python scripts/s9-pgo.py place-card
s9_build card card-pgo '-fprofile-use -Werror=coverage-mismatch' card-pgo-train
