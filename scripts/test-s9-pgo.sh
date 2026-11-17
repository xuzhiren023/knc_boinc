#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/s9-common.sh
s9_build x86 x86-base ''
s9_build x86 x86-pgo-train '-fprofile-generate -fprofile-update=atomic'
python scripts/s9-pgo.py train-x86
python scripts/s9-pgo.py place-x86
s9_build x86 x86-pgo '-fprofile-use -Werror=coverage-mismatch' x86-pgo-train
python scripts/s9-pgo.py proof-x86
