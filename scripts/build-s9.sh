#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/s9-common.sh
s9_build card card-base ''
s9_build card card-pgo-train '-fprofile-generate -fprofile-update=atomic'
cp build/s9/card-pgo-train/.build-options build/s9/card-pgo-train/.training-options
mkdir -p build/s9/runtimes
for lib in libstdc++.so.6 libgcc_s.so.1 libgomp.so.1; do
    cp -L "$S9_SHARED/gcc-knc-16.2.0/k1om-mpss-linux/lib64/$lib" build/s9/runtimes/
done
python scripts/s9-pgo.py stage
cat build/s9/pgo-train.sh build/s9/card-threads.sh
