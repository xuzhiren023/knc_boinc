#!/usr/bin/env bash
# Print only: large 60/240-thread follow-up using the existing S1-04 runner.
set -euo pipefail
cd "$(dirname "$0")/.."
[[ -f dist/card/milkyway_nbody.mic ]] || { echo 'Build first: make -C mk card' >&2; exit 1; }
mkdir -p runs/card
for threads in 60 240; do
    command=(python C:/Users/xuzhi/Documents/gcc_knc/tools/card_run --benchmark
        --threads "$threads" --timeout 43200 --receipt "runs/card/large-$threads.json"
        --file dist/card/milkyway_nbody.mic
        --file workunits/large/params.lua --file workunits/large/input.hist)
    for runtime in dist/card/*.so*; do command+=(--file "$runtime"); done
    command+=(scripts/card-launch.sh "OMP_NUM_THREADS=$threads"
        -f params.lua -h input.hist --print-histogram --seed 670828913
        --nthreads "$threads" --ignore-checkpoint --checkpoint-interval=-1 20000)
    printf "'%s' " "${command[@]}"
    printf '> runs/card/large-%s.txt 2>&1\n' "$threads"
done
