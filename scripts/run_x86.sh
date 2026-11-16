#!/usr/bin/env bash
# Run from Git Bash; outputs are deliberately gitignored.
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin:$PATH"
export OMP_DYNAMIC=FALSE
for case_name in ${1:-small medium}; do
    case "$case_name" in
        small) bodies=64 ;;
        medium) bodies=1024 ;;
        *) echo "Unknown workunit: $case_name" >&2; exit 2 ;;
    esac
    for threads in ${2:-1 4}; do
        [[ "$threads" == 1 || "$threads" == 4 ]] || exit 2
        out="runs/x86/$case_name-$threads"
        mkdir -p "$out"
        # Prevent a previous result from masking a run that produces no output.
        rm -f "$out/histogram.txt"
        export OMP_NUM_THREADS="$threads"
        command=(build/x86/milkyway_nbody.exe
            -f "workunits/$case_name/params.lua"
            -h "workunits/$case_name/input.hist"
            -z "$out/histogram.txt" -c "$out/checkpoint"
            --seed 670828913 --nthreads "$threads"
            --ignore-checkpoint --checkpoint-interval=-1 "$bodies")
        printf '%q ' "${command[@]}" > "$out/command.txt"
        printf '\n' >> "$out/command.txt"
        TIMEFORMAT='%3R'
        echo "Running $case_name with $threads thread(s)"
        set +e
        { time "${command[@]}" > "$out/stdout.txt" 2> "$out/stderr.txt"; } 2> "$out/seconds.txt"
        status=$?
        set -e
        echo "$status" > "$out/exit.txt"
        [[ "$status" == 0 ]] || { cat "$out/stderr.txt" >&2; exit "$status"; }
        python scripts/compare.py "$out" "$out"
        echo "Elapsed $(cat "$out/seconds.txt") s"
    done
    if [[ -z "${2:-}" ]]; then
        python scripts/compare.py "runs/x86/$case_name-1" "runs/x86/$case_name-4" > "runs/x86/$case_name-compare.txt"
        cat "runs/x86/$case_name-compare.txt"
    fi
done
