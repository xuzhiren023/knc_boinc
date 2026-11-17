#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/tmp build/s10-walk
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
shared=/c/Users/xuzhi/Documents/gcc_knc/.work/_shared
export PATH="$shared/toolchain/cygwin/bin:$PATH"
cc="$shared/gcc-knc-16.2.0/bin/k1om-mpss-linux-gcc"
od="$shared/toolchain/cross/bin/k1om-mpss-linux-objdump"
: > build/s10-walk/compiler-repro-missed.txt
"$cc" -O2 -march=knc -ffp-contract=off -fno-math-errno -fno-strict-aliasing \
    -fopt-info-vec-missed=build/s10-walk/compiler-repro-missed.txt \
    -c probes/s10_walk_scalar.c -o build/s10-walk/compiler-repro.o
"$od" -dr build/s10-walk/compiler-repro.o > build/s10-walk/compiler-repro.dis
for hot in 0 1; do
    for target in x86 card; do
        compiler="$cc"
        [[ $target != x86 ]] || compiler="$shared/toolchain/cygwin/bin/gcc"
        "$compiler" -O2 -S -DNBODY_WALK_HOT="$hot" -DDOUBLEPREC=1 -DDSFMT_MEXP=19937 \
            -DHAVE_CONFIG_H -Iconfig -Ithird_party/milkywayathome_client_196/nbody/include \
            -Ithird_party/milkywayathome_client_196/milkyway/include \
            -Ithird_party/milkywayathome_client_196/lua/src -Ithird_party/milkywayathome_client_196/lua/include \
            -Ithird_party/milkywayathome_client_196/popt/include -Ithird_party/milkywayathome_client_196/dSFMT -Ithird_party/milkywayathome_client_196/crlibm probes/s10_walk_layout.c \
            -o "build/s10-walk/layout-$target-$hot.s"
    done
done
python scripts/s10-walk.py assembly
