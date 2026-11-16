#!/usr/bin/env bash
# Build only; never install into a live BOINC directory or contact the card.
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin:$PATH"
mkdir -p build/tmp
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
# Sources must already have been fetched/patched with scripts/fetch.sh.
make -C mk -j6 knc-wrapper card graphics
package=dist/milkyway_package
# A fresh inventory prevents stale app versions or DLLs surviving a rebuild.
# Fixed, repository-relative generated directory only.
root_path=$(realpath .)
package_path=$(realpath -m "$package")
[[ "$package_path" == "$root_path/dist/milkyway_package" ]] || {
    echo "Package directory resolves outside the expected build destination" >&2; exit 1;
}
rm -rf -- dist/milkyway_package
mkdir -p "$package"
cp build/graphics/knc_nbody_graphics.exe "$package/"
cp build/wrapper/knc_wrapper.exe "$package/"
cp dist/card/milkyway_nbody.mic dist/card/*.so* "$package/"
# Flat project-directory files: BOINC file_info names are basenames.
sed 's/^package_dir=card$/package_dir=./' config/knc_wrapper.cfg.example > "$package/knc_wrapper.cfg.example"
# Resolve Cygwin runtime imports transitively from the supplied host toolchain.
# Windows system DLLs stay on Windows; no DLL is downloaded.
host_bin=/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin
pending=("$package/knc_wrapper.exe" "$package/knc_nbody_graphics.exe")
while ((${#pending[@]})); do
    file=${pending[0]}
    pending=("${pending[@]:1}")
    imports=$("$host_bin/objdump" -p "$file")
    while read -r dll; do
        [[ -n "$dll" ]] || continue
        if [[ ! -f "$package/$dll" ]]; then
            [[ -f "$host_bin/$dll" ]] || { echo "Missing host runtime: $dll" >&2; exit 1; }
            cp "$host_bin/$dll" "$package/$dll"
            pending+=("$package/$dll")
        fi
    done < <(printf '%s\n' "$imports" | sed -n 's/^[[:space:]]*DLL Name: \(cyg[^[:space:]]*\).*/\1/p')
done
python - "$package" <<'PY'
import pathlib
import sys
import xml.etree.ElementTree as ET

package = pathlib.Path(sys.argv[1])
root = ET.Element('app_info')
app = ET.SubElement(root, 'app')
ET.SubElement(app, 'name').text = 'milkyway_nbody'
files = sorted(p.name for p in package.iterdir() if p.is_file())
for name in files:
    info = ET.SubElement(root, 'file_info')
    ET.SubElement(info, 'name').text = name
    if name in ('knc_wrapper.exe', 'knc_nbody_graphics.exe'):
        ET.SubElement(info, 'executable')
version = ET.SubElement(root, 'app_version')
for key, value in [('app_name', 'milkyway_nbody'), ('version_num', '196'),
                   ('platform', 'windows_x86_64'), ('plan_class', 'mt'),
                   ('avg_ncpus', '1'), ('max_ncpus', '1')]:
    ET.SubElement(version, key).text = value
for name in files:
    ref = ET.SubElement(version, 'file_ref')
    ET.SubElement(ref, 'file_name').text = name
    if name == 'knc_wrapper.exe':
        ET.SubElement(ref, 'main_program')
    else:
        # Windows loader and ordinary card-package reads cannot use BOINC XML links.
        ET.SubElement(ref, 'copy_file')
        if name == 'knc_nbody_graphics.exe':
            ET.SubElement(ref, 'graphics_app')
            ET.SubElement(ref, 'open_name').text = 'graphics_app'
# indent() is unavailable in the laptop's native Python 3.8.
from xml.dom import minidom
(package / 'app_info.xml').write_text(
    minidom.parseString(ET.tostring(root)).toprettyxml(indent='  '), encoding='utf-8')
PY
python packaging/check_package.py "$package"
printf 'Package ready: %s\n' "$package"
