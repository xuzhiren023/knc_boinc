#!/usr/bin/env bash
# Assemble the no-download Windows release from an already-reviewed flat package.
set -euo pipefail
cd "$(dirname "$0")/.."
package=${1:-dist/milkyway_package}
python packaging/check_package.py "$package"
release=dist/knc-boinc-installer
mkdir -p "$release"
# Never overwrite an owner's logs or backups when assembling an update.
if [[ -e "$release/package" ]]; then
    echo 'Installer package already exists; choose a fresh worktree/release directory.' >&2
    exit 1
fi
cp packaging/installer/* "$release/"
mkdir "$release/package"
cp "$package"/* "$release/package/"
printf 'Installer ready: %s\n' "$release"
