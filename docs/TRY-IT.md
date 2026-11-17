# Try KNC BOINC on this Windows laptop

Updated 2026-11-17. Use the Windows installer folder for installation, updates,
uninstall and restore. No command prompt, Python or runtime download is needed.
Real-card science, installed Manager/screensaver behavior and service-account
SSH access still require the lead's checks; the installer does not prove them.

## Before installation

Have BOINC installed and attached to MilkyWay@home in BOINC Manager. Keep
**No new tasks** selected and existing tasks suspended until you choose a trial.
The first trial should use the interactive Windows login. The card must already
be provisioned, reachable, and reserved for your use, with Windows OpenSSH Client
available and a private key plus verified known_hosts file readable by the BOINC
account. Ask the lead to run the offline sample in the appendix before live work.

Obtain the matching **knc-boinc-installer** release folder from the lead. If it
arrives as a zip, right-click it and choose **Extract All**. Keep all its files
and the `package` subfolder together in a writable local folder outside the BOINC
data directory. Keep this folder: it will hold your logs and backups. Do not
copy a private key into the release folder or the BOINC project.

## Install or update by double-clicking

1. Open `dist/knc-boinc-installer/` in Explorer (or the extracted release folder).
   Double-click **Install KNC BOINC.cmd** and approve the Windows UAC prompt.
2. Review the settings form. It discovers BOINC paths from the registry, with
   defaults of `C:\ProgramData\BOINC` and `C:\Program Files\BOINC`. Correct them
   if needed. For the lab card use host `192.168.1.100`, user `root`, your existing
   SSH key, the verified known_hosts file, and remote base
   `/tmp/claude/claude-knc-boinc`. On updates the installed wrapper config is kept;
   the card fields in the form apply only to a first installation.
3. Click **Continue**. The installer checks BOINC, attachment/project folder,
   package inventory/manifest, and a strict, noninteractive SSH connection to
   the card. Review the confirmation dialog and select **Yes** to change files.
   Foreign `app_info.xml` or `app_config.xml` cause a clear refusal without
   changing BOINC data. An old manual installation needs lead review because
   it has no installer ownership record.
4. BOINC receives a graceful quit request. The installer waits up to 90 seconds
   without killing processes, backs up the **whole data directory**, installs
   the package, writes wrapper and single-task concurrency configs, then requests
   client/Manager restart. A timeout changes no package files: close the client
   using Manager and retry. A failed copy attempts to roll back the saved data.
5. Read the final dialog and retain its backup path and log. Each run writes a
   dated `KNC-*.log` beside the installer. Backups are in its `backups` subfolder.
   In Manager inspect the Event Log for anonymous-platform recognition and
   missing-file/version errors. Keep **No new tasks** and the other tasks
   suspended; resume one task only when you choose a card trial.

For an update, obtain a fresh matching release folder and double-click its
**Install** entry again. It replaces recorded package files and preserves
`knc_wrapper.cfg` byte for byte. Keep previous release folders for their backups.
The installer refuses modified/foreign manifests rather than merging them.

## Uninstall or restore by double-clicking

Select **No new tasks** in Manager and resolve experimental tasks with the lead
before switching application versions. Double-click **Uninstall KNC BOINC.cmd**
to remove the installer-recorded KNC files and configs while retaining stock
files and task state. Review settings and confirm; shutdown, full backup and
Manager restart use the same flow as installation.

For full rollback, double-click **Restore KNC BOINC backup.cmd**, review settings,
and select the dated backup folder containing `backup.json` and `data`. The
installer checks its identity and checksums, asks for confirmation, then saves
the current data before restoring the chosen backup. **Restore replaces all
BOINC state**: an old backup can replay already reported results. Choose a
suitable backup with the lead. The final dialog identifies the safety backup.
If automatic restart fails, open BOINC Manager from Start and retain the log.

## Appendix: developer build and fake-tree acceptance

The lead assembles the installer from an already built/reviewed package; this
copies artifacts and does not compile or contact the card:

```bash
cd /c/Users/xuzhi/Documents/knc-boinc
bash scripts/make-boinc-installer.sh
```

The release folder is `dist/knc-boinc-installer/`. Its scripts use Windows
PowerShell 5.1 and built-in Windows Forms. Keep release files out of BOINC data.
The assembler refuses an existing `package` destination to protect earlier
releases and their backups; assemble from a fresh worktree for updates.

Run the acceptance test from Git Bash; it confines data, package, mocked dialogs,
SSH and lifecycle adapters to marked fixtures under `build/installer-tests`.
It never controls BOINC, contacts the card or accesses the owner's data tree:

```bash
mkdir -p build/tmp
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe \
    -NoProfile -ExecutionPolicy Bypass -File "$(cygpath -w "$PWD/tests/installer.ps1")"
```

## Appendix: retained command-line build, offline sample and manual checks

The detailed command reference below is retained for the lead. The manual file
copy/rollback commands are for reviewed legacy installations; use the entry
points above for installer-owned deployments, whose manifest hashes/inventory
must remain consistent.

Draft, 2026-11-16. Run the offline sample first. The lead's S4-01 card run,
measured times, numerical comparison and installed-client/screensaver checks
are still pending; this guide does not claim they passed. The acceptance test
for S4-02 is the lead following **Offline sample** verbatim and recording its
exit status and comparison below. See [wrapper.md](wrapper.md),
[packaging.md](packaging.md) and [graphics.md](graphics.md) for implementation details.

### Prerequisites and shell

You need an operational Knights Corner card with MPSS/Linux, network access,
SSH enabled and enough free RAM and `/tmp` space. Card bring-up is outside this
repository. This laptop's lab card is `192.168.1.100`, login `root`; confirm those
values with its owner. Reserve exclusive card use before running a 240-thread
task. Do not run the offline sample alongside BOINC or another card job.

Use **Git for Windows Bash** for every command below, starting in the lead's
reviewed main checkout shown below. No PowerShell commands are embedded in the blocks. A source build
needs the existing GCC-KNC and Cygwin toolchain, Git, make and Python 3; do not
install CMake, MinGW or MSVC. The owner may instead use the lead's already-built
`dist/milkyway_package/` plus the matching x86 reference binary in `build/x86/`.
Keep the repository's sample inputs and comparison scripts with that package.
Do not mix artifacts from different revisions.

```bash
cd /c/Users/xuzhi/Documents/knc-boinc
export REPO="$PWD"
export PATH="/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin:$PATH"
mkdir -p build/tmp
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
export SSH=/c/Windows/System32/OpenSSH/ssh.exe
export SSH_KEY=C:/Users/xuzhi/.ssh/xeon_phi_rsa
export CARD_HOST=192.168.1.100 CARD_USER=root
export REMOTE_BASE=/tmp/knc-boinc
```

The default remote base is `/tmp/knc-boinc`. **This shared lab instead requires
files under `/tmp/claude` with names beginning `claude-`.** On this lab card run
this override before continuing; elsewhere retain the default:

```bash
export REMOTE_BASE=/tmp/claude/claude-knc-boinc
```

#### SSH key and host identity, including a fresh laptop

Windows OpenSSH Client must already be available (or enabled by the owner in
Windows Optional Features). This laptop already has the card in
`~/.ssh/known_hosts` and the key `~/.ssh/xeon_phi_rsa`; skip key creation when
that file exists. A fresh laptop can create a dedicated key as follows:

```bash
mkdir -p "$HOME/.ssh"
if [ ! -f "$HOME/.ssh/xeon_phi_rsa" ]; then
    /c/Windows/System32/OpenSSH/ssh-keygen.exe -t rsa -b 3072 \
        -f "$SSH_KEY" -C knc-boinc
fi
cat "$HOME/.ssh/xeon_phi_rsa.pub"
"$SSH" -i "$SSH_KEY" "$CARD_USER@$CARD_HOST" 'uname -a'
```

Have the card owner authorize the displayed **public** key in the login's
`~/.ssh/authorized_keys`. Never copy the private key to the card, repository or
package. At the first SSH connection, compare the displayed host fingerprint
with one obtained independently from the card owner before accepting it; this
creates the Windows login's known_hosts entry. Do not disable host-key checking.
A changed fingerprint requires investigation, not blindly deleting the entry.
For unattended use, arrange noninteractive key access (an agent available to
the same login, or an owner-approved dedicated key without a passphrase).
The wrapper cannot answer password/passphrase prompts. Verify its batch mode:

```bash
"$SSH" -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=10 \
    -i "$SSH_KEY" "$CARD_USER@$CARD_HOST" 'uname -m; df -h /tmp'
```

Expect `k1om` on the card and sufficient free space. These commands and BOINC
must run as an account that can read the key and its known_hosts. The recommended
first trial runs the BOINC client in the interactive Windows login. A BOINC
service account has different permissions/profile and needs separate provisioning;
a successful interactive SSH test does not prove service access.

### Build or use the package

If the lead supplied a matching package and x86 executable, skip the build
block. Otherwise, from the shell above (scratch exports must precede compilation):

```bash
cd "$REPO"
bash scripts/fetch.sh
make -C mk x86
bash packaging/make_package.sh
```

Only `scripts/fetch.sh` fetches the pinned sources in [SOURCES.md](../SOURCES.md).
The builder produces the wrapper, graphics app, MIC executable, host DLLs,
card runtimes and `app_info.xml`. It builds nothing on the card. Rebuilding
replaces `dist/milkyway_package/`, so keep owner configuration outside it.
Validate the supplied or built package **before** adding any owner files:

```bash
cd "$REPO"
python packaging/check_package.py dist/milkyway_package
test -s build/x86/milkyway_nbody.exe
```

### Offline sample (no BOINC account, scheduler or result upload)

This uses real SSH/card transport and the wrapper's standalone mode on the
64-body sample, followed by the identical x86 sample. BOINC need not be installed
or running. It creates a fresh slot so old checkpoints cannot contaminate it.
Keep this shell open: later blocks reuse its variables. A failing command is a
reason to stop and consult Troubleshooting, not to enable live work.

```bash
cd "$REPO"
export SLOT="$(mktemp -d "$REPO/build/try-it.XXXXXX")"
cp workunits/small/params.lua workunits/small/input.hist "$SLOT/"
export PACKAGE="$(cygpath -am "$REPO/dist/milkyway_package")"
cat > "$SLOT/knc_wrapper.cfg" <<CFG
host=$CARD_HOST
user=$CARD_USER
ssh_key=$SSH_KEY
ssh_path=C:/Windows/System32/OpenSSH/ssh.exe
scp_path=C:/Windows/System32/OpenSSH/scp.exe
remote_base=$REMOTE_BASE
package_dir=$PACKAGE
app=milkyway_nbody.mic
OMP_NUM_THREADS=240
poll_interval=10
snapshot_interval=5
connect_timeout=10
retry_limit=3
checkpoint_timeout=60
bodies=64
CFG
printf 'Offline slot: %s\n' "$SLOT"
(
    cd "$SLOT" || exit
    "$PACKAGE/knc_wrapper.exe" > wrapper_stdout.txt 2> wrapper_stderr.txt
)
wrapper_status=$?
printf '%s\n' "$wrapper_status" > "$SLOT/exit.txt"
if [ "$wrapper_status" -ne 0 ]; then
    cat "$SLOT/wrapper_stderr.txt" "$SLOT/knc_wrapper.log"
    (exit "$wrapper_status")
else
    test -s "$SLOT/histogram.txt" &&
    test -f "$SLOT/nbody_stdout.txt" &&
    test -s "$SLOT/nbody_stderr.txt" &&
    bash scripts/run_x86.sh small 1 &&
    cat "$SLOT/nbody_stdout.txt" "$SLOT/nbody_stderr.txt" > "$SLOT/card-result.txt" &&
    python scripts/compare.py runs/x86/small-1 "$SLOT/card-result.txt" \
        > "$SLOT/comparison.txt" && cat "$SLOT/comparison.txt" || {
            printf 'FAIL: inspect the slot logs and comparison.txt before continuing.\n' >&2
            false
        }
fi
```

The zero-argument wrapper uses `params.lua`, `input.hist`, seed 670828913,
64 bodies and `--print-histogram`. It is intentional for this standalone sample;
a server task uses its actual arguments instead. A successful run has exit 0,
`histogram.txt`, the two N-body logs, `knc_wrapper.log` and comparison **PASS**
with strict absolute likelihood difference **< 1e-10**. Histogram differences
are diagnostic only. x86 small's recorded 1.96 reference is
in `tests/references/nbody-1.96.json`; the comparator, not rounded text, determines the verdict.
A PASS on this sample does not establish production scientific correctness.
The N-body stdout file may be empty; the science diagnostics normally go to
stderr. No timing estimate or card result is available yet.

The standalone test has no BOINC Manager task or client IPC controls. For
suspend/resume/checkpoint and live graphics integration, the lead runs S4-01;
the laptop-only regression is `bash tests/wrapper.sh graphics` (real x86 app,
fake transport). It is not evidence of real-card acceptance.

In a second Git Bash window, repeat the shell variable setup above and inspect
the card while the offline wrapper is running (a small task may finish quickly):

```bash
"$SSH" -o BatchMode=yes -o StrictHostKeyChecking=yes -i "$SSH_KEY" \
    "$CARD_USER@$CARD_HOST" top
```

Press `q` to leave top. Look for `milkyway_nbody` and CPU activity; display and
CPU percentage conventions vary. Do not kill unrelated users' jobs. The wrapper
log records its unique `task-PID-TIMESTAMP` directory. Successful completion
removes only that task directory, leaving the remote base. Inspect the base:

```bash
"$SSH" -o BatchMode=yes -o StrictHostKeyChecking=yes -i "$SSH_KEY" \
    "$CARD_USER@$CARD_HOST" "ls -la '$REMOTE_BASE'"
cat "$SLOT/knc_wrapper.log"
```

Retain the slot for review. The lead records date, package revision, slot path,
wrapper exit, comparison, wall time and remote cleanup. **Pending S4-01:** add
measured card results and observed failures here after the lead's run; no
real-card failures have been reported in this ticket.

### Owner decision before installing BOINC

**Attaching to MilkyWay@home and returning results is the owner's decision.**
The following steps can download work and later upload scientific results.
This experimental package may be refused by the scheduler or validator, lose
work/credit, or produce incorrect results. Its pinned standard N-body 1.96 and patched
standalone behavior are not established as equivalent to the standard server
application. SSH/service permissions, checkpoint portability, real-client
staging and output declarations still require verification. An offline PASS
is insufficient to establish production readiness. Stop here for an offline-only trial.

### Capture a stock task before switching

1. Obtain the Windows installer from [boinc.berkeley.edu](https://boinc.berkeley.edu/).
   Install BOINC Manager/client and the BOINC screensaver. For the initial trial,
   choose an interactive user installation rather than protected/service mode.
   Record the installer's **data directory**, distinct from Program Files.
   The usual location is `C:/ProgramData/BOINC` (ProgramData is hidden).
2. If the owner elects a live trial, use Manager's Add Project flow and the
   official MilkyWay@home project. With the stock app, allow one standard N-body
   task to download, then immediately select **No new tasks** for the project.
   Suspend the downloaded task while inspecting it. Orbit Fitting is a different
   app; its contract does not establish standard N-body's contract.
3. Exit Manager and explicitly stop the **client**, choosing to stop running
   tasks when prompted. Closing Manager alone can leave it running. If installed
   as a service, stop BOINC through Windows Services. Confirm no `boinc.exe` or
   stock science process remains in Task Manager before reading/backing up state.

Change BOINC_DATA if necessary. This read-only extractor prints application,
command line, input/output references and result names; it never edits state:

```bash
export BOINC_DATA=/c/ProgramData/BOINC
export BOINC_STATE="$(cygpath -am "$BOINC_DATA/client_state.xml")"
python - <<'PY'
import os
import xml.etree.ElementTree as ET
root = ET.parse(os.environ['BOINC_STATE']).getroot()
## BOINC writes project records followed by sibling app/workunit/result records.
project = None
for item in root:
    if item.tag == 'project':
        project = item.findtext('master_url')
        print('PROJECT', project)
    elif item.tag == 'workunit':
        print('WORKUNIT', item.findtext('name'), 'APP', item.findtext('app_name'))
        print('COMMAND_LINE', item.findtext('command_line', default=''))
        for ref in item.findall('file_ref'):
            print('INPUT', ET.tostring(ref, encoding='unicode').strip())
    elif item.tag == 'result':
        print('RESULT', item.findtext('name'), 'WORKUNIT', item.findtext('wu_name'))
        for ref in item.findall('file_ref'):
            print('OUTPUT', ET.tostring(ref, encoding='unicode').strip())
    elif item.tag == 'app_version':
        print('APP_VERSION', item.findtext('app_name'), item.findtext('version_num'),
              'CMDLINE', item.findtext('cmdline', default=''))
PY
```

Retain a state backup and the project's downloaded inputs. An absent workunit
command line is not a license to invent one: inspect app-version command lines
and the stock slot's `init_data.xml` if necessary. Logical `open_name` can differ
from physical `file_name`. Preserve exact seed, numeric parameters and ordered
argv; XML entities must be decoded, as the extractor does. Never paste arbitrary
server text into a shell for execution. The historical 2024 example in
[packaging.md](packaging.md) is not a current standard task definition.

The owner's 2026-11-16 capture has four suspended `milkyway_nbody` 196/`mt`
tasks. Their inputs open as `nbody_parameters.lua` and `histogram.txt`; their
results declare no output files. The result travels in BOINC stderr: the
wrapper forwards the complete card stderr, including `<search_likelihood>`
and all component tags, and retains `nbody_stderr.txt` for diagnostics.
`OMP_THREAD_LIMIT=12 bash tests/wrapper.sh real-contract` exercises the captured 117676 contract
after `python scripts/real_task.py capture`. Files referenced only inside Lua
or visualizer strings are not automatically staged. Keep the four tasks
suspended and No new tasks selected until the owner chooses a card trial;
the matching anonymous version below can bind those existing tasks. Stop the
client before installation. Do not edit `client_state.xml` or the stock exe.
The fake-card test can take two hours; its host-only thread limit bounds actual
execution while still checking that the card argv requests 240. Keep that
test environment override out of real-card launches.

### Install the anonymous-platform package

Back up the whole data directory outside it while stopped. Use a shell with
permission to access the directory; resolve ACL problems deliberately rather
than running BOINC as administrator to bypass key permissions.

```bash
cd "$REPO"
export PACKAGE=/c/Users/xuzhi/Documents/knc-boinc/dist/milkyway_package
python packaging/check_package.py "$PACKAGE"
export BACKUP="$(mktemp -d "$REPO/build/boinc-backup.XXXXXX")"
cp -a "$BOINC_DATA/." "$BACKUP/"
export PROJECT="$BOINC_DATA/projects/milkyway.cs.rpi.edu_milkyway"
test -d "$PROJECT" && printf 'Project: %s\nBackup: %s\n' "$PROJECT" "$BACKUP"
```

Use the actual folder under `projects/` if the attached URL produced another
name. Existing `app_info.xml` or `app_config.xml` must be reviewed/merged first;
the commands below assume neither exists. This manifest declares only
`milkyway_nbody`, version `196`, platform `windows_x86_64`, plan class `mt`,
matching the already downloaded tasks. The lead reviews/builds the package in
**main** at the absolute `PACKAGE` path above before the owner installs it.
It replaces the project's automatic application selection.
Copy the **contents**, keeping the package flat:

```bash
if [ ! -f "$PROJECT/app_info.xml" ] && [ ! -f "$PROJECT/app_config.xml" ]; then
    cp "$PACKAGE"/* "$PROJECT/" &&
    cat > "$PROJECT/knc_wrapper.cfg" <<'CFG' &&
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
else
    printf 'Existing manifests: review and merge before installing.\n'
fi
```

Verify these lab SSH/card settings with the offline sample first. The explicit
`known_hosts=` file must be readable by the BOINC login; retain strict host-key
checking. `package_dir=.` selects the flat project layout. The wrapper reads
the config beside its executable; a slot
config overrides it. The key stays outside the project. `app_info.xml` includes
the MIC runtimes, host DLLs and graphics app as `graphics_app`. Both CPU fields
reserve **1 host CPU**. The concurrency limit is essential: otherwise BOINC can
launch several 240-thread jobs. It does not coordinate other projects/card users.
BOINC's existing `--nthreads 12` is replaced by the config's `240` on the card;
every other argument retains its order and value except resolved file paths.

Restart BOINC. In Manager's Event Log (Advanced view), check anonymous-platform
recognition and no missing-file/version/platform/plan-class errors. Keep No new
tasks selected. At the owner's chosen trial, resume one of the existing
196/`mt` tasks, leaving the other three suspended. Expect one running
task using **1 CPU**, elapsed time and progress advancing after remote polling
(not necessarily smoothly). If waiting, inspect Activity/preferences and other tasks.
The real 110,000-body task spent over an hour generating initial bodies on the
laptop before reporting evolution progress. Card startup time is unmeasured;
use process/CPU activity and logs alongside the progress display.
Suspend the task: card CPU use should stop; resume should continue it and progress.
Inspect the PID in the remote task directory's `pid` file and its state, using
this command (it prompts for that numeric PID):

```bash
read -r -p 'Card task PID: ' CARD_PID
if [[ "$CARD_PID" =~ ^[0-9]+$ ]]; then
    "$SSH" -o BatchMode=yes -o StrictHostKeyChecking=yes -i "$SSH_KEY" \
        "$CARD_USER@$CARD_HOST" "ps -o pid,stat,args -p $CARD_PID"
fi
```

Suspended state includes `T`. Use Manager controls for the test. A stopped job's
wall-clock timer is not scientific progress.

### Graphics and screensaver

After installing the reviewed anonymous-platform package above, resume one
N-body task and wait until its status is **Running**. In Manager use **View â†’
Advanced view**, open the **Tasks** tab, select that one task on this local
computer, and click **Show graphics**. A separate window should show gold stars,
blue dark matter, a Galactic-disc grid, progress and running status. The first
snapshot can take the configured snapshot interval (five seconds by default)
plus polling and transfer time; a waiting scene initially is normal. Resize the
window to check it stays readable. Suspend the task to see its last frame and
**suspended** status, then resume it. Escape closes graphics while science
continues; the button also changes to **Stop graphics** while its window runs.
Graphics closes shortly after the wrapper ends the task.

If **Show graphics** is greyed out, select only one resumed N-body task and
check that its project is resumed, computation is permitted in **Activity**,
and its status is Running rather than ready, suspended or waiting. Connect
Manager to the local computer. The reviewed package's `app_info.xml` must
reference `knc_nbody_graphics.exe` with `<open_name>graphics_app</open_name>`;
the `<graphics_app/>` marker alone is insufficient on 8.2.8. Confirm that the
file and its host DLLs are in the project directory and that Manager's task
**Properties** shows the intended anonymous application version. If discovery
is still missing, retain the Event Log and package inventory for the lead;
do not edit a running client's state or slot. See the pinned source/line audit
in [boinc-graphics-launch.md](boinc-graphics-launch.md).

Open Windows **Settings â†’ Personalization â†’ Lock screen â†’ Screen saver
settings** (or search Start for **Change screen saver**). Select **BOINC** in
the screen-saver list; if absent, the owner must install the BOINC screensaver
component. Choose a wait time and open **Settings**. Enable project application
graphics and set a nonzero project-graphics duration if offered; keep any
blank-screen timeout longer than the test interval. Click **Preview**, then
also let Windows reach the idle timeout with the task running. Settings labels
vary with the installed version. BOINC may show its default logo/status view
before switching to project graphics. Expect the same live particles and
status, filling the primary screen without a window border. Move the mouse or
press a key to leave fullscreen; science should continue. Screensaver rotation
or stop also ends its graphics helper.

Review Manager's Activity menu and computing preferences if computation is
allowed only while idle. A service/session mismatch or graphics policy can
prevent project graphics; test Show graphics in the interactive login first.
If no snapshot arrives, inspect the task's `knc_wrapper.log` and connection
status. A silent producer becomes stale after five seconds and an attached
orphan window exits after thirty seconds without a relay heartbeat. Graphics
do not prove numerical correctness or server validation.

The laptop-only regression is `bash tests/wrapper.sh graphics graphics-launch`.
Its [windowed capture](img/s11-manager-graphics.png) and
[fullscreen capture](img/s11-screensaver-graphics.png) use live x86 fake-card
snapshots. Installed Manager/screensaver behavior and a real-card live view
remain owner checks; neither the owner's client nor its data directory was
modified by that regression.

### Stop, clean up and roll back

Select No new tasks first. Prefer finishing and reporting experimental tasks
only if the owner has chosen to return results. To stop without returning them,
suspend network activity as well, then quit the client with running tasks stopped;
retain the data directory for review. Quitting requests a checkpoint and remote
cleanup. Allow acknowledgement and transfer before powering off the card, and
inspect `knc_wrapper.log`. An unreachable card or temporary exit can retain a
remote job and lease for reattachment. Do not erase its slot or `knc_remote`
lease while it may own a process. Manager's Abort kills the remote app and
removes its directory when reachable; it discards the work.

For an interrupted standalone sample, do not assume Ctrl+C cleaned the card.
Retain `$SLOT`, inspect its log/lease and the card with the owner; recover the
same slot rather than starting duplicate work. Restore connectivity before
resolving an unreachable job. Never recursively delete `remote_base` or kill
all N-body processes. Remove only the verified task folder after confirming
its process ended; leave unfamiliar jobs to their owner.

For stock BOINC rollback, drain/report or deliberately abort experimental tasks,
stop the client, and back up current state again. If there was no previous
anonymous configuration, remove these files with the client stopped:

```bash
rm -f -- "$PROJECT/app_info.xml" "$PROJECT/app_config.xml" "$PROJECT/knc_wrapper.cfg"
```

If there were previous configurations, restore those specific files from
`$BACKUP` instead. Do not restore an old `client_state.xml` over later reported
results. Restart and inspect the Event Log; the project should supply stock
apps on subsequent work requests. Retain logs, backup and local slot until
review finishes. There is no need to delete the sample slot to run BOINC.

### Troubleshooting

These are recorded repository/laptop issues and anticipated integration checks.
S4-01's real-card failure list is pending: the lead should append each observed
failure, diagnostic and verified remedy after that run.

| Symptom | Check / remedy |
| --- | --- |
| Compiler absent, Cygwin temp/traversal error | Use Git Bash, supplied Cygwin PATH and all three scratch exports above. Do not substitute compilers. |
| Fetch network/Schannel or pinned-source/patch failure | Retain the diagnostic; retry only `bash scripts/fetch.sh` after connectivity recovers. Do not bypass verification. An earlier stale Cygwin-target build failed on `direct.h`; use matching clean artifacts. |
| Windows relink executable-lock error | Close the graphics/wrapper process owning the output and retry; avoid concurrent builds into one output tree. |
| Missing host DLL | Validate the package; keep all DLLs beside its executables. Development commands require supplied Cygwin PATH. Do not download DLLs. |
| SSH timeout, refused, Permission denied, prompt or host-key failure | Verify card/network, host/user and batch command above, key access and known_hosts for the actual BOINC login. Verify changed fingerprints with the owner. |
| SSH works interactively but fails in BOINC | Inspect slot `knc_wrapper.log`, config precedence, OpenSSH paths, service ACLs and key/profile. Real service operation is unproven. |
| Repeated temporary exits | Bounded retries lead to a 60-second BOINC temporary exit. Keep lease, restore connectivity and let it reattach; do not start duplicates. |
| Remote permission, disk-space or runtime loader error | Check remote base ownership/lab rule and `df -h /tmp`; validate MIC runtime closure. k1om runs on the card, Windows executables on host. Do not replace packaged runtimes with older card GCC libraries. |
| Missing input, unknown option or required output absent | Compare current argv and logical/physical refs with pinned option rules; retain logs. Do not use the sample fallback for server work. |
| `NBODY_TREE_STRUCTURE_ERROR` on restore | The old implementation restored raw softening pointers; current patched code reconstructs them. Verify matching patched build and unchanged inputs. Retain checkpoint/logs; never reuse another task's checkpoint or assume x86/card portability. |
| Checkpoint timeout / lost heartbeat | Preserve lease/logs and restore connectivity. A fresh acknowledgement is required before cleanup; an old checkpoint file is not proof. |
| Comparator missing/ambiguous likelihood or histogram | Check wrapper exit and both N-body logs; compare `card-result.txt`, not wrapper stderr. Both sides need `--print-histogram`: saved best-step and printed final histograms differ. Use the sample input; legacy four-column histograms are incompatible. |
| Likelihood difference >= 1e-10 | Stop; preserve inputs, seed, threads, package and logs for the lead. Do not loosen tolerance. Histogram diagnostics do not decide the verdict. |
| Missing file/version/platform or stock app starts | Stop client, verify actual project folder, flat inventory, `app_info.xml`, `windows_x86_64` and Event Log. Identity 196 selects standard N-body 1.96. |
| Multiple tasks/card processes | Suspend new work; check `app_config.xml` and other card users. The manifest does not serialize access. Do not kill unrelated jobs. |
| Progress initially zero or frozen on suspend | Expected before polling/safe simulation steps or while stopped. If still frozen after resume, inspect card CPU, log and connectivity. |
| Show graphics absent/idle, screensaver blank | Verify graphics app/open name, running slot, snapshot, user session and screensaver durations. A helper launched outside its live slot has no mapping. Earlier blank screenshots were a capture issue; an image alone does not prove live attachment. |
| Scheduler/validator rejection | Keep logs/state, stop requesting work; local package/sample checks cannot establish production acceptance. Owner decides whether to roll back. |
