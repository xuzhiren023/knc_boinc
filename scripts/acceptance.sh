#!/usr/bin/env bash
# Full host acceptance, including the standard 1.96 reference/vector matrix.
set -euo pipefail
cd "$(dirname "$0")/.."
exec "$BASH" scripts/offline-196.sh "$@"
