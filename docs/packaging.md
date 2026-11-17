# MilkyWay project-directory package

`bash packaging/make_package.sh` builds `dist/milkyway_package/` from the
repository's wrapper, combined release card binary and graphics targets.
It does not install files, request work, connect to a card, or modify a BOINC installation. This is an experimental
anonymous-platform package, not a demonstrated production MilkyWay client.

## Public application survey (checked 2026-11-16)

[Applications](https://milkyway.cs.rpi.edu/milkyway/apps.php) lists standard
N-body **1.96** and Orbit Fitting **1.97**, each with plain (no displayed plan
class) and **mt** variants, on Windows x86-64, Linux x86-64 and Linux ARM64.
Their displayed creation dates are 2026-06-03 and 2026-10-28, respectively.
[Server status](https://milkyway.cs.rpi.edu/milkyway/server_status.php) names
`milkyway_nbody` and `milkyway_nbody_orbit_fitting` in the corresponding
validator/work-generator entries. This package selects `milkyway_nbody` only.
The status page's task-count snapshot was dated 2026-11-10, not the survey day.
These pages establish current advertised versions and internal app names;
they do not expose the current workunit command line or input/output templates.

A concrete, **historical** public task XML example is in
[message 77113, posted 2024-04-28](https://milkyway.cs.rpi.edu/milkyway/forum_thread.php?id=5081&postid=77113).
It is an Orbit Fitting task, version 187, with a workunit name beginning
`de_nbody_04_08_2024_v186_OCS__data__9_`. Its invocation has the form:

```text
-f nbody_parameters.lua -h histogram.txt --seed <task-seed> -np <count> -p <task-parameters...>
```

That example maps physical `EMD_v186_OCS.lua` to logical
`nbody_parameters.lua`, and `data_hist_summer_2020_beta_disp7.hist` to logical
`histogram.txt` (an input histogram). Physical names and argument values vary
by task. This is evidence of a task contract, not proof that today's standard
1.96 tasks use it. The public workunit page tried,
[workunit 963887023](https://milkyway.cs.rpi.edu/milkyway/workunit.php?wuid=963887023),
was unavailable, and public task/host listings required login. No account or
scheduler RPC was used. Consequently the **current standard N-body command
line, physical input names, and output file template could not be verified
from the allowed public pages**. Obtain a current task definition before a
live trial; do not substitute the historical Orbit Fitting template as fact.
S7-02 subsequently captured the owner's four standard 196/`mt` workunits
read-only from `C:/ProgramData/BOINC` on 2026-11-16. They use logical inputs
`nbody_parameters.lua` and `histogram.txt`, with no declared result files;
scientific results return in BOINC stderr. Exact commands, Lua body counts,
evolve times and estimates are in the S7-02 ticket report and `runs/real/tasks.json`.

## Build and check

From Git for Windows bash, with the supplied toolchains and pinned sources:

```bash
mkdir -p build/tmp
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
bash scripts/fetch.sh
bash tests/packaging.sh
# Or just build and validate:
bash packaging/make_package.sh
python packaging/check_package.py dist/milkyway_package
```

The builder sets the same scratch variables before compilation and prepends
the supplied Cygwin bin directory. It performs no fetch itself. `scripts/fetch.sh`
verifies the pinned revisions and applies the repository patches; it is the
only source-fetch entry point. No CMake, MinGW, MSVC, or installations are used.

S10 release options live in `config/release.env`: O2, tree variant 4,
derivative reuse, parallel quadrature, static integration, chunk 4, scalar
gravity and the default walk layout. Source performance options remain off
by default. The builder uses `make -j2`, builds `build/s10/card-release/`
with timers off and `build/s10/card-release-timers/` with timers on, and
packages the timers-off binary. `bash scripts/test-release.sh` retains the
12-thread exact-reference proofs in `build/s10/proof.txt` and stages
`build/s10/release-window.sh` (large and core-small, timers on, lead only).
Run packaging before that proof script so the package and runtime closure
are available for acceptance checks.

The flat package contains `knc_wrapper.exe`, `knc_nbody_graphics.exe`, the transitive Cygwin DLL imports
resolved from both executables (currently five), `knc_wrapper.cfg.example`,
`milkyway_nbody.mic`, its compiler-runtime `.so` closure, and `app_info.xml`.
Windows system DLLs, Linux system libraries, private keys, workunit inputs,
and build diagnostics are not included. Card lint/readelf/runtime provenance
remain in `dist/card/`. The graphics executable supports windowed and `--fullscreen` BOINC launches;
see [graphics.md](graphics.md) for the format, demo and window checks.
Rebuilding replaces the generated package directory; do not keep an edited
configuration or other owner files there.

The checker verifies exact case-sensitive file inventory, safe unique names,
nonempty regular files, declaration/reference agreement, the sole executable
main program, copy semantics for auxiliary files, and the single-app/one-CPU
policy. It is a local consistency check, not an XML schema, PE/ELF loader,
scheduler or scientific validator. Run it on the generated package before
adding owner configuration. `tests/packaging.sh` builds the actual targets and
also checks rejection of missing files, case errors, absent main program,
dangling refs, duplicate names, undeclared files and path traversal names.

## app_info.xml field choices

| Field | Choice and reason |
| --- | --- |
| `app/name` | `milkyway_nbody`, the standard server application identifier; the human-readable title is not the identifier. |
| `file_info/name` | Exact flat basenames for every delivered file. No absolute paths or directory separators; one declaration per file. |
| `file_info/executable` | `knc_wrapper.exe` and `knc_nbody_graphics.exe` are host executables BOINC can launch. The MIC ELF is data to the host and runs remotely. |
| `app_version/app_name` | Refers to the single declared app. |
| `version_num` | `196`, encoding pinned standard N-body 1.96 as integer hundredths. The pin matches the advertised standard app version; the patched GCC-KNC binary still needs server validation. |
| `platform` | `windows_x86_64`, describing the host wrapper, not k1om. |
| `avg_ncpus`, `max_ncpus` | Both `1`. BOINC reserves one host CPU per wrapper task; the config's 240 card threads are not host CPUs. |
| `plan_class` | `mt`, matching the owner's already downloaded 196/mt tasks. Host CPU reservation remains 1; the wrapper replaces BOINC's `--nthreads 12` with its configured card count (240). |
| `file_ref/file_name` | References each declared delivered file using its exact basename. Task input/output references belong to server task templates, not this app-version list. |
| `file_ref/main_program` | Exactly one, pointing to `knc_wrapper.exe`. |
| `file_ref/copy_file` | Every auxiliary file uses a real slot copy. DLL loading and ordinary C++ filesystem reads cannot interpret BOINC XML soft links. |
| `open_name` | Graphics only: `graphics_app`, required for discovery by the pinned client. Other slot names equal package basenames. |
| `file_ref/graphics_app` | Present on `knc_nbody_graphics.exe` as requested; pinned-client discovery also requires the open name above. |
| Command line | No app-version override. It would not remove the server's workunit arguments; see the compatibility limitation below. |
| Other optional fields | No GPU/coproc, performance estimate or API-version claim. None is established for this package. |

The pinned BOINC client's `client/app_start.cpp` obtains the main executable
path in the project directory; S2-02 locates that executable via `/proc/self/exe`
and looks for configuration beside it (slot configuration takes precedence).
The packaged example uses `package_dir=.` so its card files resolve in the
same flat project directory. This differs intentionally from the development
example's `package_dir=card` layout.

## Owner's anonymous-platform setup

First set the project to no new tasks, keep existing tasks suspended, stop the
client, and back up its data directory including any existing `app_info.xml`.
This manifest matches the captured tasks' 196/mt identity. Never edit
`client_state.xml` as an installation shortcut.

Copy the **contents** of `dist/milkyway_package/` to this project's directory
under the BOINC data directory, normally
`projects/milkyway.cs.rpi.edu_milkyway/`. Do not copy the enclosing directory.
Do not overwrite another anonymous-platform configuration without merging and
reviewing it: this manifest declares exactly one app version and replaces the
project's automatic app selection for this installation.

Copy `knc_wrapper.cfg.example` to `knc_wrapper.cfg` there and edit host, user,
key path and other settings described in [wrapper.md](wrapper.md). Keep
`package_dir=.` for this layout. Provision SSH known_hosts and key permissions
for the account actually running BOINC; the key itself stays outside the
package. Slot configuration overrides project configuration. The config is
owner-managed, deliberately absent from the generated manifest; the wrapper
reads it next to the project executable. Real service-account access remains
unproven. The existing `scripts/run_wrapper.sh SLOT` is the lead's development
launcher for a prepared task and uses the same built wrapper; it contacts the
card only when the lead invokes it with
real configuration.

Before enabling work, verify the remaining task-contract details below. After that,
restart BOINC and inspect its event log for anonymous-platform recognition,
missing files and version/platform errors. Limit the project to **one task at
a time** in the owner's `app_config.xml` (`project_max_concurrent` 1); otherwise
one host-CPU reservation per task can launch several 240-thread jobs on the
same card. This manifest itself does not serialize card access. Test a small
amount of work and inspect actual validation results before expanding use.

For rollback, stop accepting work, drain/report experimental tasks where
possible, stop BOINC, restore the backed-up app configuration (or remove this
app_info.xml if none existed), then restart and let the project supply stock
applications. Keep backups until the client is working normally.

## Compatibility limits and owner risk

S2-04 adds task argument pass-through and file staging by the pinned option
table; see [wrapper.md](wrapper.md) for the exact rules and limitations.
Laptop tests cover a historical-forum-shaped command and the sample workunit
with resolved input/output names. No scientific seed or Lua parameters are
substituted for supplied task arguments. S7-02 adds the owner's actual 117676
command and input names, with configured card threads replacing host threads.
The wrapper retains `nbody_stdout.txt` and `nbody_stderr.txt` as diagnostic
captures and forwards complete science stderr to BOINC, as required by the
captured results with no declared output files. Live-client binding and server
validation still need an owner integration run.

The server may refuse this anonymous
platform/version or the scientific validator may reject its results. The
pinned code is standard 1.96 (`1e640779`); patched standalone
behavior, compiler numerics, remote checkpoints, stdout/stderr routing and
real Windows BOINC service/sandbox behavior are not proven by packaging.
The **owner decides whether to try** and accepts possible lost work or credit.
Passing this checker does not imply scheduler acceptance, correct production
science or validation. The engineer has no card key and has not requested
work, installed the package, or run it on a real client/card.
