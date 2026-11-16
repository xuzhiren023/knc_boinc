#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ "${1:-}" == boinc ]]; then
    repo=https://github.com/BOINC/boinc.git
    tag=client_release/8.2/8.2.8
    commit=0bb9686b9ea2cb26e342c715026d8059fa58b922
    dest=third_party/boinc
    mkdir -p third_party
    if [[ ! -d "$dest/.git" ]]; then
        git -c core.autocrlf=false -c http.sslBackend=openssl clone --depth 1 --branch "$tag" --no-recurse-submodules "$repo" "$dest"
    fi
    actual=$(git -C "$dest" rev-parse HEAD)
    [[ "$actual" == "$commit" ]] || { echo "Unexpected BOINC commit: $actual (expected $commit)" >&2; exit 1; }
    for patchfile in "$PWD"/patches/boinc/*.patch; do
        if patch -d "$dest" -p1 --forward --batch --dry-run --silent < "$patchfile" >/dev/null 2>&1; then
            patch -d "$dest" --batch --forward -p1 < "$patchfile"
        elif ! patch -d "$dest" -p1 -R --batch --dry-run --silent < "$patchfile" >/dev/null 2>&1; then
            echo "BOINC source differs from expected patch state: $patchfile" >&2
            exit 1
        fi
    done
    echo "$tag $actual"
    exit 0
fi
repo=https://github.com/Milkyway-at-home/milkywayathome_client.git
tag=nbody_1.96
commit=1e640779f1cabf88aaa49e4db569cfe7e09016c4
dest=third_party/milkywayathome_client_196
mkdir -p third_party
if [[ ! -d "$dest/.git" ]]; then
    git -c core.autocrlf=false -c http.sslBackend=openssl clone --depth 1 --branch "$tag" --no-recurse-submodules "$repo" "$dest"
fi
actual=$(git -C "$dest" rev-parse HEAD)
[[ "$actual" == "$commit" ]] || { echo "Unexpected source commit: $actual (expected $commit)" >&2; exit 1; }
echo "$tag $actual"
# Cygwin already declares glob_pattern_p, just as glibc does.
for patchfile in "$PWD"/patches/*.patch; do
    if patch -d "$dest" -p1 --forward --batch --dry-run --silent < "$patchfile" >/dev/null 2>&1; then
        patch -d "$dest" --batch --forward -p1 < "$patchfile"
    elif ! patch -d "$dest" -p1 -R --batch --dry-run --silent < "$patchfile" >/dev/null 2>&1; then
        echo "Source differs from expected patch state: $patchfile" >&2
        exit 1
    fi
done

# The default fetch supplies both pinned app-side dependencies.
bash "$0" boinc
