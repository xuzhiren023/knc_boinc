# knc-boinc card runner

Run `python tools/card_run [options] program [args...]` from the knc-boinc
checkout. Card jobs remain lead-only. `--project NAME` overrides `CARD_PROJECT`;
without either, the project is `knc-boinc`. Select the project before the program
argument. The selected project tags all emitted rows and controls `is_ours` and
own-turn admission. Untagged legacy `claude-<32 hex>` rows retain upstream
ownership behavior; tagged GCC-KNC rows are foreign by default.

## Complete difference list against upstream

Source: `C:/Users/xuzhi/Documents/gcc_knc/tools/card_run`, last file commit
`5feedc3f23aff1c2807598d0bb7e2bf3d087631c`, Git blob
`7bf94b0d8e6f8435f8ba5e57a331491677519455` (clean upstream file at copy time).

1. Added the provenance header and generalized the docstring's turn project.
2. Fixed `ROOT` to `C:/Users/xuzhi/Documents/gcc_knc`, the original runner's
   resolved root, instead of deriving it from this copy's location. Import
   `card_dma` from that root's `tools` directory with bytecode writes disabled
   during import. Reuse the upstream helpers and remote shell without copying
   or editing them.
3. Changed `PROJECT` to `CARD_PROJECT`, defaulting to `knc-boinc`.
4. Added `--project` and assigned its parsed value to `PROJECT` before running.
   Existing row writers, `is_ours`, and turn matching already use this constant.

Every other line is unchanged. In particular the default config (including
`knownHosts`), `.work/_state/card.lock`, receipt directory, DMA latch and helpers
remain under GCC-KNC; `claude-admission.lock` remains beside the shared ledger.
Job IDs still use `claude-<32 hex>`, and card directories still use
`/tmp/claude/claude-<32 hex>`. Config overrides and lock semantics are unchanged.
The local copy requires the existing GCC-KNC checkout and its configured helpers.
To inspect the exact diff in bash:

```bash
diff -u /c/Users/xuzhi/Documents/gcc_knc/tools/card_run tools/card_run
```

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

All runner calls in `scripts/` now use `tools/card_run`; none exist in
`packaging/`. The S9-01 worktree was left untouched. For its already staged
`build/s9/pgo-train.sh` and `build/s9/card-threads.sh`, see
`scripts/card-run-path.sh`: it prints an absolute local runner path for the lead
to substitute after landing, preserving the staged working directory and args.

```bash
mkdir -p build/tmp
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
python -m unittest discover -s tests -p test_card_run_project.py -v
```

The five offline acceptance tests cover tagging and selection precedence,
ownership (including legacy rows), admission versus a foreign queue, turn
queue/requeue/finish and dry runs, and preserved paths/local call sites.
