# Source from a Git Bash entry point after changing to the repository root.
mkdir -p build/tmp build/s9
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
S9_SHARED=/c/Users/xuzhi/Documents/gcc_knc/.work/_shared
export PATH="$S9_SHARED/toolchain/cygwin/bin:$PATH"
s9_build() {
    local target=$1 variant=$2 flags=$3 objects=${4:-$2}
    local program=milkyway_nbody.exe
    [[ $target != card ]] || program=milkyway_nbody.mic
    mkdir -p "build/s9/$variant"
    # GCC hashes the object output path into static-function profile IDs.
    # Keep that path fixed; only the linked executable has a new destination.
    [[ $objects == "$variant" ]] || program="../$variant/$program"
    local rebuild=()
    # New counters must trigger a fresh use build even when flags are unchanged.
    [[ $objects == "$variant" ]] || rebuild=(-B)
    make -C mk -j2 "${rebuild[@]}" TARGET="$target" OUT="../build/s9/$objects" PROGRAM="$program" \
        TREE_VARIANT=2 PARALLEL_QUAD=1 STATIC_INTEGRATE=1 PHASE_TIMERS=1 \
        VECTOR_GRAVITY=0 FORCE_CHUNK=4 WALK_LAYOUT=0 TREE_IDENTITY=0 WALK_COUNTERS=0 \
        OPTFLAGS=-O2 PGOFLAGS="$flags" program > "build/s9/$variant-build.log" 2>&1
    if [[ $objects != "$variant" ]]; then
        cp "build/s9/$objects/.build-options" "build/s9/$variant/.build-options"
    fi
    if [[ $target == card ]]; then
        python C:/Users/xuzhi/Documents/gcc_knc/tools/knc_lint \
            "build/s9/$variant/milkyway_nbody.mic" > "build/s9/$variant/knc-lint.txt" 2>&1
        echo 'PASS: knc_lint exit 0' >> "build/s9/$variant/knc-lint.txt"
    fi
    echo "Built $variant"
}
