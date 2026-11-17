#!/usr/bin/env bash
# Owner-run: install the knc-boinc anonymous-platform package into the local BOINC data directory.
# Run from the knc-boinc folder in Git Bash with BOINC stopped. Backs up the BOINC data directory first.
set -euo pipefail
cd "$(dirname "$0")/.."
BOINC_DATA=${BOINC_DATA:-/c/ProgramData/BOINC}
PACKAGE=$PWD/dist/milkyway_package
PROJECT=$BOINC_DATA/projects/milkyway.cs.rpi.edu_milkyway

if tasklist //fi "imagename eq boinc.exe" | grep -qi boinc.exe; then
    echo "BOINC is still running. In BOINC Manager use File > Exit (stop running tasks), then run this again." >&2
    exit 1
fi
[ -d "$PROJECT" ] || { echo "Project folder not found: $PROJECT" >&2; exit 1; }
if [ -f "$PROJECT/app_info.xml" ] || [ -f "$PROJECT/app_config.xml" ]; then
    echo "Existing app_info.xml or app_config.xml in $PROJECT: not overwriting. Tell the lead." >&2
    exit 1
fi
python packaging/check_package.py "$PACKAGE"

BACKUP=$PWD/build/boinc-backup-$(date +%Y%m%d-%H%M%S)
mkdir -p "$BACKUP"
cp -a "$BOINC_DATA/." "$BACKUP/"
echo "Backup: $BACKUP"

cp "$PACKAGE"/* "$PROJECT/"
cat > "$PROJECT/knc_wrapper.cfg" <<'CFG'
host=192.168.1.100
user=root
ssh_key=C:/Users/xuzhi/.ssh/xeon_phi_rsa
known_hosts=C:/Users/xuzhi/Documents/gcc_knc/.work/_state/card/known_hosts
ssh_path=C:/Windows/System32/OpenSSH/ssh.exe
scp_path=C:/Windows/System32/OpenSSH/scp.exe
remote_base=/tmp/claude/claude-knc-boinc
package_dir=.
app=milkyway_nbody.mic
OMP_NUM_THREADS=240
poll_interval=10
snapshot_interval=5
connect_timeout=10
retry_limit=3
checkpoint_timeout=60
CFG
cat > "$PROJECT/app_config.xml" <<'XML'
<app_config>
  <project_max_concurrent>1</project_max_concurrent>
</app_config>
XML
echo "Installed into $PROJECT"
echo "Next: start BOINC Manager, check the Event Log, keep other tasks suspended, and tell the lead before resuming 117676."
