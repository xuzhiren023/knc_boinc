#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/s9-common.sh
bash scripts/build-tree4.sh
python scripts/s9-tree4.py proof
python tests/test_s9_tree4.py
