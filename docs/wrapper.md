# KNC BOINC task wrapper

Build from Git for Windows bash, using only the pinned sources and the supplied
Cygwin toolchain:

```bash
export PATH="/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin:$PATH"
mkdir -p build/tmp
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
bash scripts/fetch.sh
make -C mk knc-wrapper card
bash tests/wrapper.sh
```

The host binary is `build/wrapper/knc_wrapper.exe`; the card package is
`dist/card/`. Ship the five Cygwin runtime DLLs listed in
[boinc-api-on-cygwin.md](boinc-api-on-cygwin.md) with the host executable.
No card connection or card execution is performed during the acceptance test.

## Configuration

Copy `config/knc_wrapper.cfg.example` to `knc_wrapper.cfg`. The slot's config
wins; otherwise the wrapper looks beside its executable. Files contain one
`key=value` per line; blank lines and lines beginning with `#` are ignored.
Unknown keys and invalid ranges fail the task with a diagnostic.

| Key | Default / meaning |
| --- | --- |
| `host`, `user`, `ssh_key` | Required for real transport; host/user use simple DNS/account names, key is a Windows or Cygwin path |
| `ssh_path`, `scp_path` | `C:/Windows/System32/OpenSSH/ssh.exe`, `scp.exe` in the same directory |
| `remote_base` | `/tmp/knc-boinc`; absolute remote parent, never the directory removed by cleanup |
| `package_dir` | `card` beside executable; explicit relative paths resolve against config directory |
| `app` | `milkyway_nbody.mic`; package basename; fake card uses `milkyway_nbody.exe` |
| `OMP_NUM_THREADS` | 240, positive; also passed as `--nthreads` |
| `poll_interval` | 10 seconds; minimum 0.05 seconds |
| `connect_timeout` | 10 seconds; SSH connect limit, 1–600 |
| `retry_limit` | 3 retries after the first attempt, 0–100 |
| `checkpoint_timeout` | 60 seconds to acknowledge a checkpoint request |
| `bodies` | 64; legacy zero-argument sample's final argument |

SSH uses batch mode, one connection attempt and strict host-key checking.
Provision the key and known_hosts for the account running BOINC beforehand.
No password dialog is supported. Commands have a local deadline of
`connect_timeout + 5` seconds; copies have `connect_timeout + 30` seconds.
Every transport operation has bounded retries. The default poll interval does
not delay the local BOINC control loop (50 ms between checks), but a transport
operation already in progress must complete or time out first.

## Task flow and files

The real BOINC API uses the S2-01 Win32 IPC variant with
`direct_process_action=0`. Task arguments retain their order and values, except
for file operands, which resolve through `boinc_resolve_filename` and become
absolute paths in a private remote `files/` directory. Physical basenames never
determine remote names. Spaces, shell punctuation and aliases are quoted safely.
Inputs are uploaded, outputs are downloaded to the resolved host names on
success, and logical BOINC soft-link files remain intact.

The file rules come from the pinned `nbody/src/main.c` option table:

| Options | Direction |
| --- | --- |
| `-f`, `--input-file` | Input Lua |
| `-h`, `--histogram-file` | Input histogram |
| `-s`, `--match-histogram` | Input comparison histogram |
| `-z`, `--histoout-file` | Output histogram |
| `-o`, `--output-file` | Output bodies |
| `-c`, `--checkpoint` | Checkpoint input/output, also used by wrapper quit/restart |
| `--visualizer-bin` | Input visualizer executable |

Separated and attached short operands and long `--option=value` operands are
handled. Missing required inputs fail visibly. Other standalone arguments that
resolve to existing slot files are staged and returned after success, supporting
additional Lua file parameters. Other values (including numeric parameters)
pass through. `--visualizer-args` is an opaque command string, not a file option.
File names used only inside Lua, absent output names without a recognized file
option, and files referenced inside a visualizer command string cannot be
inferred from argv.

Wrapper defaults for checkpoint, checkpoint interval and thread count are added
before the task arguments only when the corresponding task option is absent.
No task seed, Lua parameters, output option or thread setting is replaced.
The environment still sets the configured `OMP_NUM_THREADS`; upstream's explicit
`--nthreads` takes precedence. The checkpoint side-file protocol uses the task's
selected checkpoint path; a checkpoint retained by upstream at successful exit
is also returned to its resolved name. Existing zero-argument development slots
retain the
legacy sample invocation (`params.lua`, `input.hist`, `histogram.txt`, seed
670828913 and config `bodies`); this fallback is not used for server arguments.
`--fake-card DIR` is consumed only as the leading wrapper transport selector.

The wrapper captures logs to resolved `nbody_stdout.txt` and `nbody_stderr.txt`.
Separate N-body log names preserve the BOINC wrapper's own `stderr.txt`
diagnostics. Current standard server output/log declarations remain unknown;
these log names must be reconciled with a current task definition before a live
trial. The 2024 Orbit Fitting example is historical evidence, not a verified
current standard workunit contract; see [packaging.md](packaging.md).

Each task stages the executable and package `.so*` files and inputs in a unique
`task-PID-TIMESTAMP` directory under `remote_base`. The slot's `knc_remote`
lease remembers it across temporary exits. A subsequent wrapper reattaches
rather than launching a second card process. An atomic remote `started`
directory makes uncertain launch retries idempotent. A launch that fails
between this guard and PID creation fails visibly; it is not blindly relaunched.

The detached `nohup sh run.sh` supervisor writes the app's PID to `pid`, captures
stdout and stderr, waits for the app and atomically publishes its `exit` code.
The app receives `OMP_NUM_THREADS`, `OMP_DYNAMIC=FALSE` and `LD_LIBRARY_PATH`
pointing at its staged runtime libraries. Polls read `progress`, `pid` and
`exit`, forwarding a clamped finite fraction to `boinc_fraction_done`.
Completion copies logs and, on success, task outputs to resolved local names,
removes only the task's directory and calls `boinc_finish` with app status.
Failures returning outputs retain the lease for a later transfer retry.

| BOINC signal | Card / slot action |
| --- | --- |
| Suspend | `kill -STOP` on the card app PID (all its OpenMP threads) |
| Resume | `kill -CONT` on that PID |
| Quit / lost heartbeat | Request a fresh checkpoint; resume a stopped app to let it write; freeze the acknowledged checkpoint, copy to slot `knc_checkpoint` via temporary file and rename, notify BOINC, kill app, remove task dir and return without `boinc_finish` |
| Restart after quit | Upload slot checkpoint to the task-selected checkpoint path (default remote `checkpoint`); preserve the task's restore/ignore options |
| Abort | `kill -KILL`, remove task directory, finish with abort status 202 |
| Unreachable card | Retry finitely, then `boinc_temporary_exit(60, diagnostic)`; preserve lease and any remote work |

If computation completes while quit is being handled, completion wins and
outputs are retrieved. A checkpoint timeout retains the lease and requests a
temporary exit rather than claiming a checkpoint was saved. App failures are
returned to BOINC after logs are copied. `knc_wrapper.log` records control,
checkpoint, retry and cleanup events; it contains no private key material.

## D6 app protocol

Upstream already supports `-c checkpoint` and checkpoint restore. Its
standalone force-loop publishes these files from the simulation thread when
`KNC_WRAPPER_FILES=1`, set by the supervisor. The minimal patch is
`patches/nbody-wrapper-files.patch`, applied by `scripts/fetch.sh`:

- `progress`: atomic rename of a temporary file containing a finite fraction
  `step / nStep` and newline, at safe step boundaries, including after restore.
- `checkpoint.request`: wrapper-created request. At a safe step boundary, write
  upstream's normal checkpoint; only on success remove the request and atomically
  publish `checkpoint.ready`. Never acknowledge a partially written checkpoint.
- `checkpoint.ready`: acknowledgment for the current request. The wrapper
  deletes old acknowledgment before making each new request and stops the app
  while downloading the checkpoint to avoid a concurrent periodic overwrite.

The pinned upstream header saves `eps2` and `eps2_index` as raw pointers,
without their pointed-to arrays. Reusing these addresses in a new process
caused the initial restart test to fail with `NBODY_TREE_STRUCTURE_ERROR`.
The opt-in restore hook rebuilds the softening context from the identical
staged Lua input, checks its array dimension, and recaches body type indices.
It preserves checkpoint bodies and the simulation step. The upstream binary
checkpoint format is unchanged; changing task inputs between runs is unsupported.
The patch reuses upstream checkpoint writing and changes no force algorithm. Without the environment variable, standalone runs do not
write wrapper side files.

## Laptop acceptance and remaining proof

`tests/wrapper.sh` uses S2-01's fake client with upstream shared memory, channels,
init-data writer and process launch. `--fake-card DIR` replaces SSH with local
Cygwin bash and scp with local file copies. It runs the actual x86 N-body build
from a fresh task directory in DIR with the same supervisor and signals.
A `.unreachable` marker in DIR deterministically fails transport attempts.
The test uses the medium model with 1024 bodies and shortens evolution and
reverse-orbit time to 0.1 Gyr to bound runtime while allowing control signals.

Two further scenarios send explicit sample and historical-forum-shaped argv,
with differing logical/physical names, body and histogram outputs, both option
operand forms, a task checkpoint, a nondefault seed, trailing numeric parameters,
and an extra Lua file parameter containing a space. The forum case also quits
and restores its task-selected checkpoint; the sample retains a checkpoint
under its resolved name on completion. They verify the actual
supervisor argv and resolved outputs using real x86 N-body.

The five original scenarios check resolved outputs and likelihood; progress frozen
under STOP then advancing under CONT; quit saving a checkpoint without finish
and restart uploading/restoring it; abort killing and cleaning; and bounded
unreachable retries producing BOINC's temporary-exit marker. Task directories
and logs remain under `build/wrapper/test.*` for review. The existing
`tests/boinc-api.sh` remains the S2-01 protocol regression test.

The real Windows OpenSSH argument/path behavior, installed BOINC service ACLs,
slot sandbox and diagnostics handling, remote Linux process lifetime, k1om
execution/checkpoint portability and real-card output correctness require the
lead's integration run. This worktree has no card key. No timing or real-card
claim is made. The laptop suite exercises real x86 N-body and real app-side BOINC code.
The card binary and runtime closure are left under `dist/card/`.

The lead can run a prepared standalone slot (config and logical files in it):

```bash
bash scripts/run_wrapper.sh /path/to/slot
# Or the same code with the x86 package configured in knc_wrapper.cfg:
bash scripts/run_wrapper.sh /path/to/slot --fake-card C:/path/to/fake-card
# Pass the prepared task's actual arguments after the transport selector:
bash scripts/run_wrapper.sh /path/to/slot --fake-card C:/path/to/fake-card \
  -f nbody_parameters.lua -h histogram.txt --seed 123456 -np 1 -p 1024
```

This launcher sets the host DLL search path and local scratch variables, then
executes the wrapper. Invoking the real-transport form contacts the configured
card; it has not been invoked by the engineer.
