#!/usr/bin/env bash
# Print only. Run from repository root so paths match the printed commands.
set -euo pipefail
cd "$(dirname "$0")/.."
[[ -f dist/card/milkyway_nbody.mic ]] || { echo 'Build first: make -C mk card' >&2; exit 1; }
mkdir -p runs/card
for spec in small:240:64 small:60:64 medium:240:1024 large:240:20000; do
    IFS=: read -r case_name threads bodies <<< "$spec"
    command=(python tools/card_run --benchmark
        --threads "$threads" --timeout 43200
        --receipt "runs/card/$case_name-$threads.json"
        --file dist/card/milkyway_nbody.mic
        --file "workunits/$case_name/params.lua" --file "workunits/$case_name/input.hist")
    for runtime in dist/card/*.so*; do command+=(--file "$runtime"); done
    command+=(scripts/card-launch.sh "OMP_NUM_THREADS=$threads"
        -f params.lua -h input.hist --print-histogram
        --seed 670828913 --nthreads "$threads" --ignore-checkpoint --checkpoint-interval=-1 "$bodies")
    # All generated tokens are fixed plain paths/options; shell-quote each token.
    printf "'%s' " "${command[@]}"
    printf '> runs/card/%s-%s.txt 2>&1\n' "$case_name" "$threads"
done
