#!/usr/bin/env bash
# Print only: the lead runs the card A/B.
set -euo pipefail
cd "$(dirname "$0")/.."
printf '# S6-03: card A/B pending; macro stays off by default.\n'
printf 'mkdir -p runs/card/vector\n'
for variant in off on; do
    for case_name in medium large; do
        bodies=1024
        [[ $case_name != large ]] || bodies=20000
        command=(python C:/Users/xuzhi/Documents/gcc_knc/tools/card_run --benchmark
            --threads 240 --timeout 43200 --receipt "runs/card/vector/$variant-$case_name.json"
            --file "build/vector/card-$variant/milkyway_nbody.mic"
            --file "workunits/$case_name/params.lua" --file "workunits/$case_name/input.hist")
        for runtime in dist/card/*.so*; do
            [[ -f $runtime ]] && command+=(--file "$runtime")
        done
        command+=(scripts/card-launch.sh OMP_NUM_THREADS=240 -f params.lua -h input.hist
            --print-histogram --seed 670828913 --nthreads 240 --ignore-checkpoint
            --checkpoint-interval=-1 "$bodies")
        printf "'%s' " "${command[@]}"
        printf '> runs/card/vector/%s-%s.txt 2>&1\n' "$variant" "$case_name"
    done
done
printf '%s\n' 'python scripts/check_vector_card.py'
