#!/usr/bin/env bash
# Lead/owner only. Existing card executable required; no builds or card access here.
set -euo pipefail
[ "$#" -ge 1 ] || { echo "usage: $0 CARD_EXECUTABLE [ARG ...]" >&2; exit 2; }
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
mkdir -p build/tmp build/s10-08
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
# Keep artifacts and receipts local to this checkout. The normal shared lock/latch applies.
python tools/card_run --transfer tcp --transport-timeout 300 --stage-timeout 600 \
  --receipt build/s10-08/tcp.json "$@"
python tools/card_run --transfer tcp-large --transport-timeout 300 --stage-timeout 600 \
  --receipt build/s10-08/tcp-large.json "$@"
# Owner may deliberately block inbound TCP externally to exercise SSH fallback.
# Never change firewall rules from this script. Avoid DMA in this smoke job.
