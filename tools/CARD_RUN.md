# knc-boinc card runner

Run `python tools/card_run [options] program [args...]` from this checkout.
Card jobs remain lead-only. `--project NAME` overrides `CARD_PROJECT`, default
`knc-boinc`, and controls tagging, ownership and own-turn admission. Untagged
legacy `claude-<32 hex>` rows retain upstream ownership behavior.

## Complete difference list against upstream

Runner source: `C:/Users/xuzhi/Documents/gcc_knc/tools/card_run`, upstream commit
`5feedc3f23aff1c2807598d0bb7e2bf3d087631c`, Git blob
`7bf94b0d8e6f8435f8ba5e57a331491677519455` at original copy time.

1. Added provenance and generalized the docstring's turn project.
2. `ROOT` is this knc-boinc checkout; `UPSTREAM_ROOT` is
   `C:/Users/xuzhi/Documents/gcc_knc`. Import upstream `card_dma` with bytecode
   writes disabled; reuse the read-only connection config and helper binaries.
3. Set `PROJECT` from `CARD_PROJECT`, default `knc-boinc`; added `--project` and
   assigned it before running. Existing row writers and ownership checks use it.
4. Move per-tool writable defaults as listed below. Create our default lock
   parent on first use; resolve `--file-list` entries against this checkout.
   Hold upstream's card-wide `card.lock` in addition to our local execution
   lock for the whole job, even with custom `--lock`. Check the shared stop
   latch before connecting and again after taking the card lock.
5. Default transfer is `auto` with a **1 MiB** DMA threshold (owner 2026-11-17, after ssh measured ~20 KB/s to the card: a 48 MB job upload took ~40 min). Files below 1 MiB go by ssh, larger ones (program, runtimes) by DMA, under the shared card-wide DMA latch and lock. `--transfer ssh` remains available.
   Below it use SSH; at or above it try DMA. Explicit `--transfer ssh` and
   `--transfer dma` remain available. Fallback is limited to DMA unavailable
   before endpoints open (`kind=unavailable`, `data_started=false`); never
   replay a started DMA transfer. Integrity and uncertain-cleanup stops remain.
   Allow `--collect` over the SSH helper pipe when both helpers are present.
6. Default transport timeout is **120 seconds**, with a floor on the old config's
   10-second value. Explicit `--transport-timeout` overrides it. Staging retains
   its separate 120-second overall budget. On a loaded laptop, increase both
   (e.g. `--transport-timeout 300 --stage-timeout 600`) rather than retry.
   Do not start DMA while the laptop is saturated.
7. Store generated upload bytes in local scratch and remove each after upload.
   Load our local shell for every session, upload, download and watchdog;
   change staging, validation and stale cleanup to
   `/tmp/knc-boinc/claude-<32 hex>`. Job IDs remain `claude-<32 hex>`.

`tools/card_run_remote.sh` is a correctness/portability copy of upstream's shell
(SHA256 `f048e0df97f050730f638dbf3d234ddee9890e376abbd74df3ef266e3786aa61`
at copy time). Only its provenance comment and logical/physical parent directory
change. Exact shape guards reject foreign `/tmp/claude/` paths; stale scans use
only our prefix. Normal file-transfer mode in `transfer_bench.c` accepts regular
filenames without that prefix restriction. Its separate benchmark **lease** mode
and `host_card_transfer.LEASE_DIRECTORY` require `/tmp/claude/`; our runner does
not use that mode. No binary rebuild is needed for the file protocol.

These are correctness/portability and file-protocol changes; no new patch file,
performance option or instrumentation is introduced. To inspect:

```bash
diff -u /c/Users/xuzhi/Documents/gcc_knc/tools/card_run tools/card_run
diff -u /c/Users/xuzhi/Documents/gcc_knc/tools/card_run_remote.sh tools/card_run_remote.sh
```

## Host and card paths

`G` = `C:/Users/xuzhi/Documents/gcc_knc`, `B` =
`C:/Users/xuzhi/Documents/knc-boinc`, `W` = this checkout (main or ticket).
`main_root(W)` is `B`, so all our worktrees share local state. Explicit output
arguments select caller paths. Config `ownLock`/`--lock` must select a local
path and cannot bypass the mandatory card-wide lock.

| Path / role | Old | New | Shared or per-tool; why |
| --- | --- | --- | --- |
| DMA stop latch | `G/.work/_state/card-dma-active.lock` | Unchanged | Must stay card-wide: uncertain SCIF cleanup stops both tools, including SSH jobs. |
| Card-wide execution/DMA lock | `G/.work/_state/card.lock` | Unchanged, mandatory alongside local lock | Must stay shared: GCC-KNC holds it for the whole job. We hold the same lock, so DMA cannot overlap; no new ignored DMA lock. |
| Local execution lock | Previously card-wide lock alone | `B/.work/_state/card.lock` | Per-tool: serializes our worktrees; overrides cannot bypass card-wide lock. |
| Retained receipts (last 200) | `G/.work/_state/card/` | `B/.work/_state/card/` | Per-tool job history. |
| Default CLI receipt | `G/tests/out/card-result.json` | `B/.work/_state/card-result.json` | Per-tool latest result. |
| Default collected outputs | `G/tests/out/collected/` | `B/.work/_state/collected/` | Per-tool job outputs. |
| Generated host scratch | Helper parent, normally `G/.work/_shared/claude-input-*` | `B/.work/_state/card-scratch/claude-input-*` | Per-tool writable bytes; executables stay read-only. |
| Ledger (`config.ledger`) | `C:/Users/xuzhi/Documents/card-coordination/jobs.jsonl` | Unchanged | Must stay shared for job and turn admission. |
| Admission lock | `claude-admission.lock` beside selected ledger | Unchanged | Must stay shared for atomic cross-project admission. |
| Config / identity / known hosts | `G/config/card.local.json`, paths selected there | Unchanged | Read-only connection settings; strict host-key checks remain. |
| Python transfer helper | `G/tools/card_dma.py` | Unchanged | Read-only implementation; no upstream bytecode writes. |
| Remote shell helper | `G/tools/card_run_remote.sh` | `W/tools/card_run_remote.sh` | Per-tool namespace guards, loaded read-only into sessions. |
| Helper / Cygwin binaries | `G/.work/_shared/` or config overrides | Unchanged | Reused read-only executables; no scratch beside them. |
| External locks | Caller-configured paths | Unchanged | Shared where configured; checked, never removed. |
| Card directories / physical aliases | `/tmp/claude/claude-*`, physical `/tmp` alias plus `/claude/claude-*` | `/tmp/knc-boinc/claude-*`, physical alias plus `/knc-boinc/claude-*` | Per-tool; watchdog, stale reaper and cleanup cannot target upstream directories. |
| Recovery archives | None | `B/.work/_state/dma-recovery/*.json` | Per-tool durable copy before shared latch deletion. |

## DMA recovery (lead/owner only)

Run `python tools/card_dma_recover.py` to inspect. Default dry run prints checks
(a)-(c) and proposed actions (d)-(e) without changing card, latch or archives.
`--confirm` is explicit lead/owner sign-off. Confirm mode takes the same shared
card lock; an existing lock refuses recovery. Engineer sessions cannot confirm.
It never reboots or kills processes.

(a) Host `host_card_transfer.event_log()` must exactly equal latch `host_state`
(boot and bugcheck record). (b) No host `claude-transfer.exe` may exist.
(c) Card boot ID must equal latch `boot_id`, with no `claude-transfer` process.
Unreadable inventories refuse recovery. If any check differs, clear nothing and
consult the owner; reboot is the owner's decision.

Only after all checks pass, `--confirm` (d) rechecks card health and guards the
exact owned directory before removing it including `claude-dma-active`, then
(e) saves, flushes and verifies an archive of the unchanged latch before deleting
it. A changed latch, unsafe path or removal/archive failure retains the latch.
Recovery accepts only our `/tmp/knc-boinc/` shape. A shared latch naming
`/tmp/claude/` belongs to GCC-KNC and requires its owner's recovery; this tool
refuses to remove their directory. A stale shared lock also needs owner review.
Normal card_run never retries or clears a latch automatically.

```bash
# Lead/owner only; inspect the printed checks first.
python tools/card_dma_recover.py
# After lead/owner sign-off:
python tools/card_dma_recover.py --confirm
```

## Transfer budgets and command generators

Use an idle laptop for DMA. On a loaded host raise both budgets rather than
retrying, e.g. `--transport-timeout 300 --stage-timeout 600`. Default transport
and overall staging budgets are each 120 seconds; increasing just transport
does not enlarge the overall staging deadline.

Audited every script and build-command generator calling card_run:
`card-check.sh`, `flags-card-commands.sh`, `multicore-card-commands.sh`,
`probe-commands.sh`, `quad-card-command.sh`, `s8-card-commands.sh`,
`vector-card-commands.sh`, `s8_integration.py`, `s9-pgo.py`, `s9-df.py`,
`s9-tree3.py`, `s9-tree4.py`, and `s10-release.py`. None overrides transfer,
threshold or transport timeout; generated `build/s8-09/*`, `build/s9/*` and
`build/s10/*` jobs inherit the new defaults. PGO's `--collect` keeps its helper
pipe for small results. No already-generated card scripts were present in this
worktree. `card-run-path.sh` only prints the local runner path. No call-site
edits are needed.

## Turn lifecycle

No turn was booked by this ticket. After landing, the lead can use these commands
from the checkout root (global options precede the action):

```bash
python tools/card_turn.py --dry-run queue --purpose 'knc-boinc benchmark window'
python tools/card_turn.py queue --purpose 'knc-boinc benchmark window'
python tools/card_turn.py requeue claude-turn-knc-boinc-<UTC-stamp>
python tools/card_turn.py finish claude-turn-knc-boinc-<UTC-stamp> --outcome success
```

Each command prints the emitted JSON line(s). Copy the returned `jobId` for the
next action. `queue` appends a `queued` row with `agent: claude`,
`project: knc-boinc`, `cores: []`, `timingValid: true`, a purpose, and timezone
aware UTC `queuedTime`. IDs use `claude-turn-knc-boinc-YYYYMMDDTHHMMSSffffffZ`.
`finish` appends the same turn's fields with `event: finish`, `endTime`, and the
required outcome. It and `requeue` reject foreign or already closed turns.

Queued turn rows are live for **three hours from `queuedTime`**, with
`timingValid` exactly `true`. A waiting lead should explicitly `requeue` at about
**2.5 hours**, then track the newly printed ID. Requeue appends `superseded` for
the old ID and a fresh queued row with the same purpose, together in one append
syscall. Renewal loses the old FIFO position: an older foreign queue goes first.
An expired but unclosed turn can still be requeued or finished. There is no
background renewal. An own turn only precedes later foreign queues; running
jobs must drain before benchmark admission.

The default ledger is `C:/Users/xuzhi/Documents/card-coordination/jobs.jsonl`.
`--ledger PATH` selects an existing alternative ledger; `--dry-run` previews
any action without appending. Tests use temporary ledgers exclusively.

## Staged commands and tests

Audited every caller in `scripts/`: `card-check.sh`, `flags-card-commands.sh`,
`multicore-card-commands.sh`, `probe-commands.sh`, `quad-card-command.sh`,
`s8-card-commands.sh`, `vector-card-commands.sh`, `s8_integration.py`,
`s9-df.py`, `s9-pgo.py`, `s9-tree3.py`, `s9-tree4.py`, and `s10-release.py`.
All use `tools/card_run` and none overrides transfer, threshold or transport
timeout, so they inherit auto at 64 MiB and the larger transport budget.
This includes generators for `build/s8-09/`, `build/s9/` (including DF and tree
subdirectories), and `build/s10/` job scripts. No staged
job scripts existed under this ticket's `build/` at the audit; no callers exist
in `packaging/`. No generator changes were necessary.

The S9-01 worktree was left untouched. For its already staged
`build/s9/pgo-train.sh` and `build/s9/card-threads.sh`,
`scripts/card-run-path.sh` prints an absolute local runner path for the lead to
substitute after landing, preserving the staged working directory and args.
The new default also applies through that path. PGO collection remains supported
with auto routing through the helper pipe.

```bash
mkdir -p build/tmp
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
python -m unittest discover -s tests -p 'test_card_run*.py' -v
```

The five S9-02 tests still pass (old path assertions reflect the new per-tool
contract). Four S10-04 tests cover per-tool state and foreign-path shell
rejection, actual shared-latch writes and card-wide lock contention with fake
transport, 64 MiB routing and preflight-only fallback, and dry-run/confirmed
recovery refusal for each changed health check. All writes use test temp paths;
no real card or transfer-helper process runs. Run both suites with:

```bash
python -m unittest discover -s tests -p 'test_card_run*.py' -v
bash -n tools/card_run_remote.sh
```
