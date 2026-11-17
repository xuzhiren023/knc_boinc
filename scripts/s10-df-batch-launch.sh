#!/bin/sh
# Lead-only native launch. Verify the compact CPU list before using it.
set -eu
while [ "$#" -gt 0 ]; do
    case "$1" in *=*) export "$1";shift;; *) break;; esac
done
if [ "${DF_BATCH_AFFINITY:-0}" = 1 ]; then
    unset OMP_PLACES
    core=0
    seen=" "
    read -r os_core < /sys/devices/system/cpu/cpu0/topology/core_id
    while [ "$core" -lt 60 ]; do
        cpu=$((1 + 4 * core))
        read -r first < "/sys/devices/system/cpu/cpu$cpu/topology/core_id"
        [ "$first" != "$os_core" ] || { echo 'affinity: OS core in worker list' >&2;exit 2; }
        case "$seen" in *" $first "*) echo 'affinity: repeated core' >&2;exit 2;; esac
        seen="$seen$first "
        lane=1
        while [ "$lane" -lt 4 ]; do
            sibling=$((cpu + lane))
            read -r actual < "/sys/devices/system/cpu/cpu$sibling/topology/core_id"
            [ "$actual" = "$first" ] || { echo 'affinity: compact CPU group is not siblings' >&2;exit 2; }
            lane=$((lane + 1))
        done
        core=$((core + 1))
    done
    echo 'DF_BATCH affinity: verified 60 compact four-sibling CPU groups (1..240)' >&2
fi
[ "$#" -gt 0 ] || exit 2
export OMP_DYNAMIC=FALSE
exec "$@"
