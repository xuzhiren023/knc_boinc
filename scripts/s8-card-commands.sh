#!/usr/bin/env bash
# Print only. Lead runs these commands from this worktree.
set -euo pipefail
cd "$(dirname "$0")/.."
printf 'mkdir -p runs/card/s8\n'
for variant in card-timers card-timers-static; do
    command=(python tools/card_run --benchmark
        --threads 240 --timeout 43200 --receipt "runs/card/s8/$variant.json"
        --file "build/s8/$variant/milkyway_nbody.mic"
        --file workunits/large/params.lua --file workunits/large/input.hist
        --file dist/card/libstdc++.so.6 --file dist/card/libgcc_s.so.1 --file dist/card/libgomp.so.1
        scripts/card-launch.sh OMP_NUM_THREADS=240 -f params.lua -h input.hist
        --print-histogram --seed 670828913 --nthreads 240 --ignore-checkpoint
        --checkpoint-interval=-1 20000)
    printf "'%s' " "${command[@]}"
    printf '> runs/card/s8/%s.txt 2>&1\n' "$variant"
done
