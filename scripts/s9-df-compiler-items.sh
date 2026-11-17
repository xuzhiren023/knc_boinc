#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/s9-df-common.sh
cc="$S9_DF_SHARED/gcc-knc-16.2.0/bin/k1om-mpss-linux-gcc"
for mode in opaque pure; do
    flags=()
    [[ $mode != pure ]] || flags=(-DSAMPLES_READ_ONLY)
    "$cc" -O2 -march=knc -fno-math-errno -ffp-contract=off "${flags[@]}" \
        -fopt-info-vec-missed="build/s9/df/reuse-$mode-missed.txt" \
        -S probes/s8_df_reuse.c -o "build/s9/df/reuse-$mode.s"
done
set +e
"$cc" -O2 -march=knc -fno-math-errno -mveclibabi=knc -fopt-info-vec-missed \
    -S probes/s9_df_ball_abi.c -o build/s9/df/ball-abi.s > build/s9/df/ball-abi.txt 2>&1
status=$?
set -e
cat build/s9/df/ball-abi.txt
if [[ $status == 0 ]]; then
    echo 'Compiler now accepts the reduced aggregate ABI; revisit archived experiment.'
else
    grep -q 'unsupported KNC register ABI mode' build/s9/df/ball-abi.txt
    echo "Reproduced compiler item (exit $status)."
fi
