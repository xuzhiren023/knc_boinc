#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin:$PATH"
mkdir -p build/tmp build/s11/science/{off,on}
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
export OMP_NUM_THREADS=4 OMP_DYNAMIC=FALSE
make -C mk -j2 x86
root=$(cygpath -am .)
args=(4.90652 1 0.386382 0.20556 1.74668 0.0420765 46.125 15.623 -215.279 114.242 181.825 353270 1.21041 2.87629)
for mode in off on; do
    (
        cd "build/s11/science/$mode"
        unset KNC_WRAPPER_FILES
        [[ "$mode" != on ]] || export KNC_WRAPPER_FILES=1
        "$root/build/x86/milkyway_nbody.exe" -f "$root/workunits/core-small/params.lua" \
            -h "$root/workunits/core-small/OCS_data_2025_north_194.hist" -z histogram.txt \
            --seed 65477096 --nthreads 4 --checkpoint-interval=-1 --ignore-checkpoint \
            -np 14 -p "${args[@]}" > stdout.txt 2> stderr.txt
    )
done
python tests/check_s11_science.py
