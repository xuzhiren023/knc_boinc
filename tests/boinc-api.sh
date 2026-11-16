#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
toolchain=$(cygpath -u "C:/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin")
export PATH="$toolchain:$PATH"
mkdir -p build/tmp
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
make -C mk boinc-api boinc-api-test
app=$(cygpath -aw build/boinc/boinc_app.exe)
client=$(cygpath -aw build/boinc/boinc_fake_client.exe)
# Fresh slot dirs retain logs and artifacts and avoid old success markers.
run=$(mktemp -d "$PWD/build/boinc/test.XXXXXX")
for mode in local global; do
    mkdir "$run/$mode"
    (cd "$run/$mode"; "$client" "$app" "$mode")
done
mkdir "$run/standalone"
(cd "$run/standalone"; "$app" >stdout.txt 2>stderr.txt; grep 'PASS standalone' stdout.txt; test -f boinc_finish_called)
echo "Logs: $run"
