#!/bin/bash
# Deterministic transport/IPC fixture; actual science identity is checked separately.
printf '%s\n' "$@" > argv
output=
while (($#)); do
    case "$1" in
        -z|--histoout-file) shift; output=$1 ;;
        --histoout-file=*) output=$(printf '%s' "$1" | cut -d= -f2-) ;;
    esac
    shift
done
for n in 0 250 500 750 1000; do
    printf '%s 1000\n' "$n" > generation.tmp
    mv generation.tmp generation
    sleep 3
done
for n in 0 .25 .5 .75 1; do
    printf '%s\n' "$n" > progress.tmp
    mv progress.tmp progress
    sleep 2
done
printf '<search_likelihood>-1</search_likelihood>\n' >&2

[[ -z "$output" ]] || printf "fixture histogram
" > "$output"
