#!/usr/bin/env bash
# Resolve compiler-runtime closure using NEEDED; glibc/loader stay on the card.
set -euo pipefail
cd "$(dirname "$0")/.."
shared=/cygdrive/c/Users/xuzhi/Documents/gcc_knc/.work/_shared
readelf="$shared/toolchain/cross/bin/k1om-mpss-linux-readelf"
runtime="$shared/gcc-knc-16.2.0/k1om-mpss-linux/lib64"
mkdir -p dist/card
cp "${1:-build/card/milkyway_nbody.mic}" dist/card/milkyway_nbody.mic
pending=(dist/card/milkyway_nbody.mic)
declare -A seen=()
: > dist/card/runtime-manifest.txt
while ((${#pending[@]})); do
    file=${pending[0]}
    pending=("${pending[@]:1}")
    [[ -z ${seen[$file]:-} ]] || continue
    seen[$file]=1
    # Keep parsing in this Bash process. On this supplied toolchain Cygwin
    # Bash can find Git/MSYS sed; crossing those runtimes loses sed's \1.
    while IFS= read -r line; do
        [[ "$line" == *"(NEEDED)"*"["*"]"* ]] || continue
        name=${line#*'['}
        name=${name%%']'*}
        if [[ -f "$runtime/$name" ]]; then
            cp -L "$runtime/$name" "dist/card/$name"
            printf '%s <- %s\n' "$name" "$runtime/$name" >> dist/card/runtime-manifest.txt
            pending+=("dist/card/$name")
        else
            case "$name" in
                libc.so.*|libm.so.*|libpthread.so.*|libdl.so.*|librt.so.*|ld-linux-k1om.so.*) ;;
                *) echo "Unresolved non-system runtime: $name" >&2; exit 1 ;;
            esac
        fi
    done < <("$readelf" -d "$file")
done
chmod 755 dist/card/milkyway_nbody.mic
chmod 644 dist/card/*.so* dist/card/runtime-manifest.txt
"$readelf" -h dist/card/milkyway_nbody.mic > dist/card/readelf.txt
"$readelf" -d dist/card/milkyway_nbody.mic >> dist/card/readelf.txt
python C:/Users/xuzhi/Documents/gcc_knc/tools/knc_lint dist/card/milkyway_nbody.mic > dist/card/knc-lint.txt 2>&1
printf 'PASS: knc_lint exit 0\n' >> dist/card/knc-lint.txt
cat dist/card/knc-lint.txt
