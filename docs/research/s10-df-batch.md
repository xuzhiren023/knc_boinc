# S10-10 batched distribution-function setup

`DF_BATCH=1` is an off-by-default **Performance** option on S10-09's vector8
kernel. The selected build uses exact scalar log/atan per lane and the inherited
empirical guard (margin 6.7163549441806109e-08). It requires DF_SPECIAL,
DF_VECTOR8, reuse, parallel quadrature and OpenMP. GEN_PIPELINE must be off.
Unsupported/cold models, nested calls and guard exact replays use the original
path. No compiler-scheduling or vector-math implementation was changed.

Golden-section speculation covers both branches two levels deep: six candidate
integrals, with the initial two points included in the first wave. That first
wave also includes four rejection attempts drawn from a copied dSFMT state,
for twelve integrals total. Subsequent max-search waves have six integrals.
The initial four attempts cover about 86% under a geometric prior with mean
2.56; actual counts and waste are measured. Exhausting them dispatches waves
of eight attempts. The final wave is shortened at the original 1002-attempt
limit. Lookahead never changes the real RNG. Each consumed attempt commits
exactly its original two draws; the first accepted attempt wins in order.

The cache is local to one velocity's radius/models/component. It uses bitwise
velocity keys, original multiply/add grouping and original comparisons and
termination tests. Every quadrature plan copies the original truncated constants,
node recurrence, 100000-counter limit, sign and serial accumulation order.
Only independent node evaluations run concurrently. Allocation failure returns
to the existing distribution evaluator for that integral. The guard can replay
the complete velocity from its saved RNG state. This guard remains empirical;
host comparisons and the lead's native likelihood tests are the acceptance.

Whole contiguous vector-block ranges are assigned to groups of four threads.
At 240 threads, each of 60 groups owns a shard of one integral. With twelve
integrals, five cores share an integral; six integrals use ten cores each. Node
arrays are not replicated across those cores. No worker writes another worker's
node, although boundary cache lines can be shared. All unsupported team sizes
have complete nonoverlapping coverage; the harness checks sizes 1 through 240.

The GCC-KNC libgomp source uses core places and default spread, making siblings
`t,t+60,t+120,t+180`. The window overrides that with explicit Linux CPU affinity
1 through 240 in order and OMP_PROC_BIND=TRUE. On this card's compact Linux CPU
numbering, these form 60 consecutive groups of four siblings, excluding the OS
core. The native launch script verifies each group from sysfs before the batch
binary runs. No native affinity result is claimed before that launch.

`working-set.json` gives the node-shard and local-stack model and its exclusions.
It is arithmetic about footprint and available blocks, not a calibrated timing
prediction. The linked math-library stack and root-preparation footprint are
outside its L1 budget. Native cache residency remains unproven.

Reproduce with bash (the build/test entry points set TMPDIR, TMP and TEMP to
`$PWD/build/tmp`, export OMP_NUM_THREADS=4 and use make -j2):

```bash
bash scripts/test-s10-df-batch.sh --measure
bash scripts/test-s10-df-batch.sh
```

The retained harness compares batches against the same vector evaluator
bitwise, compares the original max finder and full velocity/RNG chain, exercises
every acceptance position across batches through the original attempt limit,
and checks schedule coverage and unsupported fallback. Short-case captures
compare every generated body and every initialized RNG word with release.
Timing includes diagnostic body/RNG output and runs one heavy job at a time.
There is no full 117676 host launch.

`twin-s10-df-batch.py` inspects capabilities and the diagnostic KNC ELF, verifies
Dwarf offsets, and audits the full node closure and its cut at real math-library
calls. Four-context 1/2/4-integral requests preserve the compiled worker. Real
node captures come from the same pinned S10-09 core-small model/seed and their
SHA256 is retained. Unsupported calls are never assigned fabricated costs.
Null cycles/constraints mean the model stopped; they do not establish occupancy.
The detailed engine fields and wall-time command ledger are in twin-results.json.

Before native execution, `prediction.json` freezes uncalibrated hypotheses.
`build/s10/df-batch/card-window.sh` stages exact and batch binaries for core-small
and real-steps with `--transfer tcp-large`, matching runtimes, binary hashes and
receipts. The engineer does not run that script. After the lead runs it:

```bash
bash scripts/test-s10-df-batch.sh --card
```

Native likelihood bits must match release for both cases. Pending receipts
skip only that test in ordinary offline acceptance; `--card` fails when absent.
