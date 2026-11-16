#!/usr/bin/env bash
# Lead's standalone wrapper launcher; real transport uses the slot config/key.
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
slot=${1:?usage: run_wrapper.sh SLOT [--fake-card DIR] [TASK_ARGS...]}
shift
slot=$(cd "$slot" && pwd)
cd "$root"
export PATH="/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin:$PATH"
mkdir -p build/tmp
export TMPDIR="$root/build/tmp" TMP="$root/build/tmp" TEMP="$root/build/tmp"
wrapper=$(cygpath -aw "$root/build/wrapper/knc_wrapper.exe")
cd "$slot"
exec "$wrapper" "$@"
