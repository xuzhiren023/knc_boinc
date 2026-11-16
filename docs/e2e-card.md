# End-to-end card run

Prepare outside the card window, from the ticket worktree in Git Bash:

```bash
mkdir -p build/tmp
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
PATH="/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin:$PATH" make -C mk -j6 boinc-api-test x86
bash packaging/make_package.sh
python tests/test_e2e_card.py
bash scripts/e2e_card.sh --dry-run --case medium --threads 4
```

In an interactive Windows card window:

```bash
bash scripts/e2e_card.sh --case medium --threads 4
# Short window: unchanged 20,000-body large workunit (~60 s at 240 threads).
bash scripts/e2e_card.sh --case large --threads 240
```

The launcher checks the shared JSONL ledger before any card commands. Open
foreign or unknown project reservations block it, including queued turns.
Missing or malformed ledgers also block it. Only after another session has
granted its turn may the lead add `--in-granted-turn`. No ledger writes occur.

Before either dry or live execution, the launcher reads `knownHosts` from
`C:/Users/xuzhi/Documents/gcc_knc/config/card.local.json` and requires that file
to exist. Both verification SSH and every wrapper SSH/SCP use
`-o UserKnownHostsFile=<knownHosts>` with `StrictHostKeyChecking=yes`. The wrapper
receives the path through its optional `known_hosts` configuration setting.
The ordinary `~/.ssh/known_hosts` has a stale card key. Missing/malformed config,
missing `knownHosts`, or a missing host-key file fails before any transport.
Printed `card_run` commands include `--benchmark` for admission within a granted
turn while another project's queue row is live.

The launcher builds nothing. It uses the packaged wrapper, graphics and card
payload, plus the prebuilt S2 fake client and x86 reference executable. The fake
client owns real BOINC Windows shared memory and sends real process-control
messages; the wrapper uses Windows OpenSSH to the real card. Files stay beneath
`/tmp/claude/claude-knc-boinc/task-<pid>-<time>`.

After a live snapshot arrives, the scenario runs 60 seconds, starts graphics
halfway through that phase, suspends, verifies `ps -o stat=` is `T` in one SSH
call, holds suspension for 30 seconds, resumes, verifies a checkpoint exists,
and quits through the wrapper's acknowledged checkpoint transfer. It retains
the restart bytes as `slot/restart-checkpoint`, verifies remote cleanup,
restarts from the slot checkpoint, and requires the upstream restore diagnostic
and successful completion. It checks both task PIDs are gone, both remote
directories are absent, and no supervisor or descendant retains either lease
as its working directory (including deleted directories). The original
workunit, seed and body count are retained.
For large only, the screenshot trigger is 2 seconds after the first live
snapshot, suspension is triggered at 5 seconds after that snapshot, suspension
lasts 5 seconds, and the checkpoint check/quit follows 2 seconds after resume.
The client receives this timing choice through `KNC_E2E_LARGE=1`; medium and
small retain their original 30/60/30/2-second timings. Large uses the unchanged
`workunits/large` inputs and 20,000 bodies for both card and x86 comparison.
These early triggers leave useful computation for the checkpoint restart within
the approximately 60-second card workload at 240 threads. The same stopped-state,
checkpoint-transfer, restore-diagnostic, cleanup and final comparison checks apply.
If a case completes before the control sequence, the scenario fails explicitly.

Each run creates `runs/e2e/<UTC timestamp>/summary.json`, phase wall times in
`e2e-times.tsv`, `client.log`, `transport.log` for verification SSH calls,
`knc_wrapper.log`, `suspend-ps.txt`, the complete slot and outputs, the fresh
single-thread x86 reference and `compare.txt`. Comparison uses the strict
absolute likelihood difference `< 1e-10`. The graphics consumer captures its
live OpenGL framebuffer to BMP; the launcher converts that bitmap to PNG using
the Python standard library, preserving `live-card.png` in the run and at
`docs/img/live-card.png` during suspension. No demo snapshot is substituted.

The dry run requires the local card config and known-hosts file, but needs no
private-key access, card, binaries or free ledger turn. It prints all
transport operation templates, twice for the two launches, with concrete
packaged runtime names when available. Runtime-generated leases, PIDs, polling
and retry counts are necessarily symbolic; the status and snapshot commands
repeat throughout the live run. It creates no run/slot and launches no client,
reference, graphics or transport process.

On failure, evidence and a FAIL summary remain. The client asks the wrapper to
abort through IPC so the wrapper can clean the real task. If transport fails,
the wrapper may retain a lease for recovery; inspect `slot/knc_remote` and the
logs before another attempt. A failed run never asserts unverified cleanup.
