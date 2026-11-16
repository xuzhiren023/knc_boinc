#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
repo=https://github.com/Milkyway-at-home/milkywayathome_client.git
tag=nbody_1.97
commit=d78c48fc9905ee309e28ae4b76ad2f6fda901ef8
dest=third_party/milkywayathome_client
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
