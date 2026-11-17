#!/bin/sh
# Usage: card-launch-env.sh [VAR=VALUE ...] program [argument ...]
set -eu
while [ "$#" -gt 0 ]; do
    case "$1" in
        *=*) export "$1"; shift ;;
        *) break ;;
    esac
done
[ "$#" -gt 0 ] || { echo 'missing program' >&2; exit 2; }
export OMP_DYNAMIC=FALSE
exec "$@"
