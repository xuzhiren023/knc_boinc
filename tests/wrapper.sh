#!/usr/bin/env bash
# Five acceptance flows, through the S2-01 Win32 shared-memory fake client.
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin:$PATH"
mkdir -p build/tmp
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
make -C mk -j6 knc-wrapper boinc-api-test x86
wrapper=$(cygpath -aw build/wrapper/knc_wrapper.exe)
client=$(cygpath -aw build/boinc/boinc_fake_client.exe)
run=$(mktemp -d build/wrapper/test.XXXXXX)
for scenario in normal suspend quit abort unreachable; do
    slot="$run/$scenario"
    mkdir -p "$slot/card" "$slot/package"
    cp build/x86/milkyway_nbody.exe "$slot/package/milkyway_nbody.exe"
    cp workunits/medium/params.lua "$slot/params.data"
    # Keep a real N-body run long enough to control, but bound the suite.
    sed -i -e 's/timeEvolve = 3.945/timeEvolve = 0.1/' -e 's/tstop     = 4.0/tstop     = 0.1/' "$slot/params.data"
    cp workunits/medium/input.hist "$slot/hist.data"
    # BOINC soft links exercise resolution in both directions.
    printf '<soft_link>params.data</soft_link>\n' > "$slot/params.lua"
    printf '<soft_link>hist.data</soft_link>\n' > "$slot/input.hist"
    printf '<soft_link>result.data</soft_link>\n' > "$slot/histogram.txt"
    cat > "$slot/knc_wrapper.cfg" <<CFG
package_dir=$(cygpath -am "$slot/package")
app=milkyway_nbody.exe
OMP_NUM_THREADS=1
poll_interval=0.1
connect_timeout=2
retry_limit=2
checkpoint_timeout=15
bodies=1024
CFG
    if [[ "$scenario" == unreachable ]]; then touch "$slot/card/.unreachable"; fi
    export KNC_FAKE_CARD=$(cygpath -am "$slot/card")
    (cd "$slot"; "$client" "$wrapper" local "$scenario")
done
python scripts/compare.py "$run/normal/nbody_stderr.txt" "$run/quit/nbody_stderr.txt"
printf 'PASS wrapper acceptance; logs: %s\n' "$run"
