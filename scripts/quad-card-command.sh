#!/usr/bin/env bash
# Print-only S7-01 window-script handoff; no card access by the engineer.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p runs/card/s8-quad
command=(python tools/card_run
    --benchmark --threads 240 --timeout 43200
    --receipt runs/card/s8-quad/core-small-240.json
    --file build/s8/card-quad/milkyway_nbody.mic
    --file workunits/core-small/params.lua
    --file workunits/core-small/OCS_data_2025_north_194.hist
    --file dist/card/libgomp.so.1
    --file dist/card/libstdc++.so.6
    --file dist/card/libgcc_s.so.1
    scripts/card-launch.sh OMP_NUM_THREADS=240
    -f params.lua -h OCS_data_2025_north_194.hist --print-histogram
    --seed 65477096 --nthreads 240 --ignore-checkpoint --checkpoint-interval=-1
    -np 14 -p 4.90652 1 0.386382 0.20556 1.74668 0.0420765 46.125 15.623
    -215.279 114.242 181.825 353270 1.21041 2.87629)
printf "'%s' " "${command[@]}"
echo '> runs/card/s8-quad/core-small-240.txt 2>&1'
