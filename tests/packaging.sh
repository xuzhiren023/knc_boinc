#!/usr/bin/env bash
# S2-03 acceptance: build the real package, then check its file contract.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/tmp
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
bash packaging/make_package.sh
python tests/test_packaging.py
