#!/usr/bin/env bash
# Task contracts and five control flows through the S2-01 shared-memory client.
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin:$PATH"
mkdir -p build/tmp
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
make -C mk -j6 knc-wrapper boinc-api-test x86 graphics
wrapper=$(cygpath -aw build/wrapper/knc_wrapper.exe)
client=$(cygpath -au build/boinc/boinc_fake_client.exe)
run=$(mktemp -d build/wrapper/test.XXXXXX)
scenarios=("$@")
if [[ ${#scenarios[@]} == 0 ]]; then
    scenarios=(forum-contract sample-contract normal suspend quit abort unreachable graphics)
fi
for scenario in "${scenarios[@]}"; do
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
snapshot_interval=0.2
bodies=1024
CFG
    if [[ "$scenario" == unreachable ]]; then touch "$slot/card/.unreachable"; fi
    export KNC_FAKE_CARD=$(cygpath -am "$slot/card")
    export KNC_GRAPHICS_EXE=$(cygpath -aw build/graphics/knc_nbody_graphics.exe)
    export KNC_TASK_ARGS=
    mode="$scenario"
    if [[ "$scenario" == *-contract ]]; then
        mode=normal
        printf '<soft_link>bodies.data</soft_link>\n' > "$slot/bodies.out"
        printf '<soft_link>checkpoint.data</soft_link>\n' > "$slot/task.chk"
        if [[ "$scenario" == forum-contract ]]; then
            mode=quit
            mv "$slot/params.lua" "$slot/nbody_parameters.lua"
            mv "$slot/input.hist" "$slot/histogram.txt"
            printf '<soft_link>result.data</soft_link>\n' > "$slot/generated.hist"
            printf '<soft_link>extra.data</soft_link>\n' > "$slot/extra name.txt"
            printf 'extra input\n' > "$slot/extra.data"
            KNC_TASK_ARGS='-f nbody_parameters.lua -h histogram.txt --seed 123456 -z generated.hist -o bodies.out --checkpoint=task.chk --nthreads 1 -np 4 -p 1024 1.25 -2.5 "extra name.txt"'
        else
            KNC_TASK_ARGS='--input-file=params.lua --histogram-file=input.hist --histoout-file=histogram.txt --output-file=bodies.out --seed 670828913 --nthreads=1 --checkpoint=task.chk --no-clean-checkpoint --checkpoint-interval=2 1024'
        fi
    fi
    (cd "$slot"; "$client" "$wrapper" local "$mode")
    if [[ "$scenario" == *-contract ]]; then
        python tests/test_wrapper_contract.py "$slot" "$scenario"
    fi
done
if [[ -f "$run/normal/nbody_stderr.txt" && -f "$run/quit/nbody_stderr.txt" ]]; then
    python scripts/compare.py "$run/normal/nbody_stderr.txt" "$run/quit/nbody_stderr.txt"
fi
printf 'PASS wrapper acceptance; logs: %s\n' "$run"
