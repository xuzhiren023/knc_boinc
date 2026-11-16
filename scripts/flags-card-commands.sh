#!/usr/bin/env bash
# Print-only A/B handoff; the lead runs the printed commands on the card.
set -euo pipefail
cd "$(dirname "$0")/.."
top=$(python -c "import json; print(json.load(open('twin/flags/evidence.json'))['top_candidate'])")
mkdir -p runs/card/flags
for variant in V0 "$top"; do
    for spec in small:1:64 small:240:64 medium:240:1024 large:60:20000 large:240:20000; do
        IFS=: read -r case_name threads bodies <<< "$spec"
        command=(python C:/Users/xuzhi/Documents/gcc_knc/tools/card_run --benchmark
            --threads "$threads" --timeout 43200
            --receipt "runs/card/flags/$variant-$case_name-$threads.json"
            --file "build/flags/$variant/milkyway_nbody.mic"
            --file "workunits/$case_name/params.lua" --file "workunits/$case_name/input.hist")
        for runtime in dist/card/*.so*; do command+=(--file "$runtime"); done
        command+=(scripts/card-launch.sh "OMP_NUM_THREADS=$threads"
            -f params.lua -h input.hist --print-histogram --seed 670828913
            --nthreads "$threads" --ignore-checkpoint --checkpoint-interval=-1 "$bodies")
        printf "'%s' " "${command[@]}"
        printf '> runs/card/flags/%s-%s-%s.txt 2>&1\n' "$variant" "$case_name" "$threads"
    done
done
