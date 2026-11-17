#!/usr/bin/env bash
# Lead only: execute during an authorized card window. No card access at staging.
set -euo pipefail
cd "$(dirname "$0")/.."
binary="${CARD_BINARY:-../S10-01/build/s10/card-release-timers/milkyway_nbody.mic}"
runtime=/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/gcc-knc-16.2.0/k1om-mpss-linux/lib64
test -f "$binary"
mkdir -p runs/card/real-benchmarks
args=(--seed 65477096 --nthreads 240 --print-histogram --ignore-checkpoint --checkpoint-interval=-1
      -np 14 -p 4.90652 1 0.386382 0.20556 1.74668 0.0420765 46.125 15.623 -215.279 114.242 181.825 353270 1.21041 2.87629)
for case in core-small real-steps; do
    python tools/card_run --benchmark --threads 240 --timeout 1800 \
        --receipt "runs/card/real-benchmarks/$case.json" \
        --file "$binary" --file "workunits/$case/params.lua" \
        --file "workunits/$case/OCS_data_2025_north_194.hist" \
        --file "$runtime/libgcc_s.so.1" --file "$runtime/libgomp.so.1" --file "$runtime/libstdc++.so.6" \
        scripts/card-launch-env.sh OMP_NUM_THREADS=240 ./milkyway_nbody.mic \
        -f params.lua -h OCS_data_2025_north_194.hist "${args[@]}" \
        > "runs/card/real-benchmarks/$case.txt" 2>&1
done
