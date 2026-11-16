#!/bin/sh
# card_run stages this program as claude-program. No host paths on the card.
set -eu
export "$1"
shift
export OMP_DYNAMIC=FALSE
exec ./milkyway_nbody.mic "$@"
