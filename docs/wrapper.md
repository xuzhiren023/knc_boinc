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
| `known_hosts` | Optional explicit host-key file for the BOINC login; lab path is in [TRY-IT.md](TRY-IT.md) |
| `ssh_path`, `scp_path` | `C:/Windows/System32/OpenSSH/ssh.exe`, `scp.exe` in the same directory |
| `remote_base` | `/tmp/knc-boinc`; absolute remote parent, never the directory removed by cleanup |
| `package_dir` | `card` beside executable; explicit relative paths resolve against config directory |
| `app` | `milkyway_nbody.mic`; package basename; fake card uses `milkyway_nbody.exe` |
| `OMP_NUM_THREADS` | 240, positive; also passed as `--nthreads` |
| `poll_interval` | 10 seconds; minimum 0.05 seconds |
| `connect_timeout` | 10 seconds; SSH connect limit, 1â€“600 |
| `retry_limit` | 3 retries after the first attempt, 0â€“100 |
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
for the thread operand (always replaced by configured `OMP_NUM_THREADS`) and
file operands, which resolve through `boinc_resolve_filename` and become
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
An explicit `--nthreads`, `--nthreads=`, or `-n` operand is replaced in place
by the configured count: the owner's BOINC `--nthreads 12` must launch 240
threads on the card. No task seed, Lua parameter or output option is replaced.
The environment also sets the configured `OMP_NUM_THREADS`. The checkpoint side-file protocol uses the task's
selected checkpoint path; a checkpoint retained by upstream at successful exit
is also returned to its resolved name. Existing zero-argument development slots
retain the
legacy sample invocation (`params.lua`, `input.hist`, `histogram.txt`, seed
670828913 and config `bodies`); this fallback is not used for server arguments.
`--fake-card DIR` is consumed only as the leading wrapper transport selector.

The wrapper captures logs to resolved `nbody_stdout.txt` and `nbody_stderr.txt`.
The entire downloaded science stderr is also forwarded, once at completion,
to the wrapper's own BOINC `stderr.txt`, on success or scientific failure.
The standalone card app emits upstream's `<search_application>` tag when the
wrapper file protocol is enabled; likelihood and component tags retain upstream
formatting. The owner's 2026-11-16 standard 196/`mt` tasks declare no result
files: BOINC stderr is the result channel. The 117676 acceptance case uses the
captured inputs and exact argv, with no invented histogram/body output option.

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

## S11 setup progress, checkpoint cadence and card turns

With the wrapper file protocol enabled, the mixed-dwarf generator atomically
publishes `generation` as `completed total` before the sampling loop, every 64
completed bodies, and at the end. This is an Instrumentation patch, separate
from the correctness file protocol and all performance patches. The wrapper
assigns **75% to generation** (`0.75 * completed / total`) and **25% to forward
steps** (`0.75 + 0.25 * step / nStep`). These are stage weights, not an ETA.
Graphics display `Generating stars N / total` in the window title and scene
until a simulation progress file appears. Restore, or a generator without body
count instrumentation, reports simulation progress directly. Graphics retain
raw simulation fractions in snapshot files; the reader applies the same weights
when generation counts are available. The shared structure keeps its size and
snapshot offset; two formerly reserved words now carry generation counts, and
status 4 means generation. Ship the rebuilt wrapper and graphics together.

`checkpoint_interval` defaults to **120 seconds**, range 1â€“86400. An explicit
upstream `--checkpoint-interval` / `-w` task operand still takes precedence.
Requested BOINC quit checkpoints bypass the periodic interval. The upstream
standalone scheduler compares integer wall time using `>`; interval 1 normally
means roughly two seconds between safe-step writes. Run
`bash scripts/measure-checkpoint-cost.sh` for an isolated 110,000-body probe of
the actual scheduler and writer, with four host threads. It reports writer wall
cost and bytes for ten seconds each at interval 1 and 120; it does not generate
or evolve 110,000 bodies, flush disk caches, or predict card filesystem latency.

`card_booking=1` is the default. `booking_ledger` defaults to
`C:/Users/xuzhi/Documents/card-coordination/jobs.jsonl` and must already exist.
The wrapper appends `tools/card_turn.py`-shaped knc-boinc queued/finish rows and
stores its open ID in the slot's `knc_turn`. It never repairs/truncates a ledger.
Earlier live foreign queues block admission; all open foreign running jobs must
drain, including jobs recorded with legacy `job_id`. Finished/end/superseded
rows close their IDs. Only `timingValid: true` queues aged 0â€“3 hours are live.
At 2.5 hours the wrapper stops the app and appends superseded+queued together,
losing its old position, then waits for admission before continuing. A restart
reattaches the saved turn and stops any existing process before admission.

After `booking_suspend_timeout` seconds suspended (default 300, range 1â€“10800),
the turn closes. Resume queues again and waits with the app stopped. Normal
completion, abort, and successful checkpoint quit close the turn. Abort and quit
also work while waiting before launch. An uncertain remote launch or unreachable
live lease retains its turn and remote directory for reattachment; the wrapper
cannot safely claim that unknown remote work has ended. Ledger errors fail
closed. Turn rows are append-only bookings, matching the manual turn tool; this
wrapper uses SSH transport, not the card runner's DMA transfer helpers.

`card_booking=0` disables ledger reads/writes. The shared DMA stop latch remains
mandatory: `dma_stop_latch` defaults to
`C:/Users/xuzhi/Documents/gcc_knc/.work/_state/card-dma-active.lock`. Its presence
blocks initial staging, launch and resume, even with booking disabled. The
wrapper never removes it. Path overrides support isolated fake-card acceptance;
production configurations should use the shared paths.

The lead-only smoke command is:

    bash scripts/s11-card-smoke.sh OWNER_CONFIG

It prepares core-small under build/s11/card-smoke, uses the rebuilt package,
enables booking, checks the reference likelihood, and refuses to overwrite a
retained remote lease/turn. The engineer syntax-checks this script only; invoking
it uses real transport and the owner's config.
