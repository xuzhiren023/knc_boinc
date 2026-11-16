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
| `bodies` | 64; upstream model's final argument |

SSH uses batch mode, one connection attempt and strict host-key checking.
Provision the key and known_hosts for the account running BOINC beforehand.
No password dialog is supported. Commands have a local deadline of
`connect_timeout + 5` seconds; copies have `connect_timeout + 30` seconds.
Every transport operation has bounded retries. The default poll interval does
not delay the local BOINC control loop (50 ms between checks), but a transport
operation already in progress must complete or time out first.

## Task flow and files

The real BOINC API uses the S2-01 Win32 IPC variant with
`direct_process_action=0`. It resolves logical `params.lua` and `input.hist`
and the outputs `histogram.txt`, `nbody_stdout.txt`, `nbody_stderr.txt`. The model and seed
are the existing standalone N-body invocation; seed is 670828913. Declare all
five logical names in the task definition. Separate N-body log names preserve
the BOINC wrapper's own `stderr.txt` diagnostics.

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
Completion copies logs and, on success, the histogram to resolved local names,
removes only the task's directory and calls `boinc_finish` with app status.
Failures returning outputs retain the lease for a later transfer retry.

| BOINC signal | Card / slot action |
| --- | --- |
| Suspend | `kill -STOP` on the card app PID (all its OpenMP threads) |
| Resume | `kill -CONT` on that PID |
| Quit / lost heartbeat | Request a fresh checkpoint; resume a stopped app to let it write; freeze the acknowledged checkpoint, copy to slot `knc_checkpoint` via temporary file and rename, notify BOINC, kill app, remove task dir and return without `boinc_finish` |
| Restart after quit | Upload slot checkpoint as remote `checkpoint`; omit `--ignore-checkpoint` so upstream restores it |
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

The five scenarios check resolved outputs and likelihood; progress frozen
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
```

This launcher sets the host DLL search path and local scratch variables, then
executes the wrapper. Invoking the real-transport form contacts the configured
card; it has not been invoked by the engineer.
