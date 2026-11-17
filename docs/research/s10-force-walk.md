# S10-02 force walk: predeclared model and card measurement plan

Prepared before new timed runs. Use knc-optimize's minimal model accounting:
model-first is not installed. Source data: S8-08's counted actual large tree in
`docs/research/s8-force-model.md`; S9-06 card measurement supplied by this ticket.
Use S9-06 options (TREE_VARIANT=4, PARALLEL_QUAD=1, STATIC_INTEGRATE=1,
FORCE_CHUNK=4, O2); S10-01 release.env is absent in this checkout. DF_REUSE=0.

## Model table

| Term | Formula / counted inputs | Value | Source, scope, assumptions |
|---|---|---|---|
| Walk work | V=1,087,300,798 visits; I=892,867,454 accepted interactions | 489.8 visits/target | S8-08, 2,220,000 targets, same large workload; tree4 preserves tree |
| FP work | 8V+10I+38C, C=697,048,696 | 44.115 Gop | Source arithmetic only, includes sqrt/div as one op |
| x87 overlapping service scenario | max(1.03A,2M,37.94D)/(60*1.232e9) | 1.632 s | S8-08 matching throughput forms, omits sqrt, shuffles, control, loads/spills |
| x87 additive service scenario | (1.03A+2M+37.94D)/(60*1.232e9) | 2.469 s | Only a conditional floor if all services serialize |
| Memory latency scenario | 2,413,473,249 lines *356.53/(240*1.232e9) | 2.910 s | Every per-target line cold, one chain/context, idle latency; not an unconditional bound |
| Cold bandwidth scenario | lines*64/186.14e9 | 0.830 s | Read sweep rate, no cross-target reuse; not actual channel traffic |
| Parallel span | max(thread work)/mean(thread work) | unknown until profile | Dynamic chunk4, 240 threads; nodes/interactions are work proxies, not equal-cost units |
| Address/control/spills | emitted instructions per visit/path | assembly audit pending | Static counts do not establish dynamic cost |
| Prefetch overhead | <=2 hints + guarded successor loads/visit | <=2.175e9 hints | No copy/scatter; extra issue/traffic can outweigh overlapped latency |
| Hot layout | unchanged node/body/cell size; hot fields move together | offsets audited by build | Constructed directly by existing tree code inside pool; no force-time conversion |
| Existing T_meas | force/whole | 12.70/15.89 s | Ticket S9-06, not reproduced here |

T_lb: no new unconditional useful walk bound; ideal FP peak floor is 0.0368 s
under the ticket's 1.2 TFLOPS assumption. Dominant competing terms are scalar
service and dependent misses, with parallel span unmeasured. Amdahl cap from
12.70/15.89 is 4.98x whole-program for a free force phase. This does not predict
that such a gain is attainable. No hand arithmetic rewrite of compiler costs.

T_pred (hypotheses, not calibrated forecasts): baseline force 12.7 s; prefetch
11.4–14.6 s (0–15% latency reduction vs up to 15% added issue/cache cost); hot
11.4–14.0 s (0–10% reduced line footprint vs cache-placement cost); both
10.8–15.2 s (effects need not add). Scheduling profile builds 12.1–16.5 s:
chunk1 may reduce tail or add dispatch contention; guided may reduce dispatch
or create a larger tail. Whole-run scenarios add the fixed non-force 3.19 s.
These bands are engineering priors for the large case, not bounds or twin output.
Core-small remains an exactness/regression control; absolute prediction unknown.

## Measurement plan

Eight jobs only: large uninstrumented baseline; large WALK_PROFILE dynamic4,
dynamic1, guided4; large uninstrumented prefetch, hot, combined; core-small
combined. All at 240 threads with identical launcher/affinity/runtime. Per-thread
rows include idle threads, actual team size, accumulated nbGravity elapsed time,
active loop duration before its barrier, target count, visited nodes, accepted
interactions and accepted cells. Counters are local per call and accumulated
into thread-local storage. Two wall-clock reads per target perturb the profile;
compare its phase total against uninstrumented baseline to quantify that cost.
Never subtract thread times from phase wall time. Sum counters, compute max/mean
and coefficient of variation separately for time and work, and inspect the tail
across every map. Schedule variants change only the scalar force loop.

Use `python scripts/s10-walk.py analyze-card` after receipts are collected to
summarize each profile; recorded predictions must remain unchanged. A large
imbalance suggests scheduling; balanced counts but uneven time suggests stalls
or placement; balanced time with a slow force phase points toward per-walk cost.
The software counts cannot distinguish DRAM, L2, branch or sqrt cost. These
require a subsequent operator measurement if the eight jobs do not resolve it.

Host ranking uses sequential 12-thread full-run evidence; report force phase,
whole time, and spread. Host ranking is provisional for KNC. Exact proof compares
all force xyz bytes at every map plus scripts/compare.py on small/medium/large
at 1 and 12 threads. Layout fields are never serialized by copying the old tree.
Checkpoint node offsets differ under WALK_HOT; checkpoint files must be used
with the same option set. Tree cells themselves are reconstructed at restart.

The launcher publishes redirected BOINC `stderr.txt` to the runner stream and
collects `claude-stderr.txt` plus `claude-histogram.txt` into each job's local
subdirectory before remote cleanup. Profile parsing accepts the streamed job
logs or the collected stderr files. This avoids losing the measurements when
standalone BOINC redirects application diagnostics away from the process stderr.

Only performance candidates (prefetch, hot, combined) need the full six-run
matrix. The three profiling/schedule builds are diagnostic large/12-thread runs,
checked against the same force stream and counted baseline. Scalar force goldens
are copied with SHA-256 provenance from S8-08's actual 1- and 12-thread streams
(which must match); the new baseline is also checked on large at both thread
counts. This avoids redundant small/medium diagnostic runs. Host timing uses
three interleaved 12-thread large runs per performance candidate and baseline,
with dump/capture environment variables absent. Proof I/O is inside the force
phase and its timings are excluded from the ranking.

## Emitted assembly and Compiler items

`build/s10-walk/assembly.json` is generated from the linked card baseline;
`nbGravity.dis`, `nbMapForceBody._omp_fn.0.dis`, and `nbGravMap.dis` retain bytes
and addresses. These are static sites, not weighted runtime instruction counts.
The scalar walk has 199 decoded instructions, 6 fxch, 29 FP accesses addressed
from rsp/rbp, 54 FP memory-operand sites (including loads/stores), one fsqrt and
four x87 divide sites. Its frame is 0x68 bytes. Several stores deliberately
round temporaries to binary64; the audit does not claim all are avoidable spills.

- Entry spills target xyz to rsp+0x18/0x20/0x28; each node reloads them. The
  three acceleration components live at rsp+0x8/0/0x10 and are updated through
  memory operands and stores. Quadrupole intermediates use rsp+0x30/0x38.
  Six fxch sites occur on the quad path. Register pressure and scalar double
  staying on x87 are compiler questions, not a reason to reorder app arithmetic.
- The accepted-interaction path copies eps2[0:2] into an addressed stack array
  on each interaction (two unconditional load/store pairs; the DM case fetches
  eps2[2] on its branch). Target type is reloaded too. Investigate invariant
  hoisting and scalar replacement of this indexed local array in GCC-KNC.
- Distance -> softened distance -> fsqrt -> mass/r -> phi/d is a serial chain.
  Quad adds reciprocal of d*d*r and the final phi/d division. Legal scheduling
  of independent quad multiplies around that chain is a compiler item. No
  reciprocal, approximate sqrt, contraction or reassociation is authorized.
- Memory forms such as fsubrl (node position), faddl (stack accumulators), and
  fmuls (2.5 constant) need the twin's x87 memory-operand serialization model;
  counting only FP operations misses these issue/address/decode costs.
- The loop body begins at 0x405077; cells jump backward to the opening test at
  0x405058. Opening failure pops four x87 stack entries and follows More;
  accepted nonself interactions fall into arithmetic. No-quad and body paths
  jump forward to duplicated stack cleanup, then join Next. Self goes to a
  cold forward block. nbReportTreeIncest is retained out of line at 0x40525a,
  with no fabricated callee cost. Alignment NOPs and branch directions are
  retained in binary twin conversion.

The OpenMP outlined caller has 296 decoded sites, 5 fxch, and 82 stack FP
accesses. It calls nbGravity, LMCAcceleration, nbExtAcceleration (or the Lua
closure), and dynamic-loop runtime functions. nbGravMap includes tree creation,
phase clock calls and team dispatch. Thus the historical 12.70 s force phase
is not an isolated gravity-walk measurement. WALK_PROFILE's accumulated walk
and active duration are intended to expose that omitted caller work: per-thread
active-minus-walk includes external potential, dispatch, clock/counter overhead
and time between chunks, not an isolated hardware-stall counter.

Reduced repro: `probes/s10_walk_scalar.c`; `bash scripts/s10-walk-compiler.sh`
compiles it with O2/march=knc, strict grouping/no contraction, emits disassembly
and `compiler-repro-missed.txt`. The vectorizer reports unsupported control flow
in the linked pointer walk. These findings are GCC-KNC leads, not demonstrated
speedups, and no compiler scheduling/vectorization patch is implemented here.

Host/card ABI probes agree. Baseline/hot node/body/cell sizes are 64/96/160
bytes. Baseline mass/rcrit/quad/More offsets are 40/64/80/72; hot offsets are
32/40/64/128. The hot version places pos/mass/rcrit before the quad block and
moves the opening link later. That can help opening tests but can also hurt
prefetch of More; cell stride and total pool bytes are unchanged. This tradeoff
is explicitly left to the native comparison.

The laptop has unrelated compute jobs running (observed read-only; left alone).
Host timing is therefore a contended-host ranking, not an isolated causal KNC
prediction. Correctness runs use PASSIVE OpenMP waiting and GOMP_SPINCOUNT=0 to
keep laptop load down; the first completed runs retain their original waiting
policy, recorded per row. All still request 1 or 12 threads with dynamic teams
disabled. Benchmark runs retain the original runtime waiting settings and record
them separately. Completed proof streams can be reused only after binary SHA,
exit status and force-stream SHA validation, followed by the exact comparisons.

`python scripts/capture-s10-walk.py` freezes complete actual initial 20,000-body
snapshots for baseline, prefetch, hot and combined. It stops only its own host
capture process after the tree snapshot is fully closed, and records this as a
capture, never a completed science/timing run. Full proof runs use separate
snapshot filenames. The twin retains every instruction of card nbGravity and
all captured node bytes, plus an independent binary64 source-order Python oracle
for four targets. Profile: card-7120-measured, one core/four contexts, cold line
tracking, predicted branches, 53-bit x87 rounding, no stubs or model overlays.
Whole-card extrapolation is not performed. Capture provenance and raw ABI probes
must match before simulation. A failed status is retained, never a partial rank.

## Pre-card twin results

All whole-function conversions and all four-output functional checks passed.
One core, four contexts, four actual initial-tree targets, identical profile and
scenario. The unit is one body walked (completion cycles divided by four calls).
These are **unvalidated_scenario_estimate** results, not card measurements.

| Candidate | Core cycles/body | Ratio to baseline |
|---|---:|---:|
| Baseline | 148351.00 | 1.0000 |
| Guarded in-place prefetch | 143625.25 | 0.9681 |
| Hot tree-time fields | 149401.00 | 1.0071 |
| Both | 145924.50 | 0.9836 |

The 0.7–3.2% differences do not pick a winner under knc-optimize's approximately
20% decision rule; all go to the card. Nothing here predicts a 4–5x recovery.
The baseline executes 204,485 dynamic instructions for four targets. Its leading
stall tallies are resource (697,359 context-cycles), miss (372,241), dependency
(350,791), x87 serialization (265,049). These overlapping per-context tallies
must not be added to form core elapsed time. Prefetch reduces modeled misses
but adds issue/resource work; hot layout alone does not improve this sample.

The shared assumptions are 53-bit x87 precision with extended exponent, LRU
private L1/L2 without coherence, 64-entry 4 KiB DTLB and a 29-cycle miss term,
page-stream L2 prefetch, a 20-cycle per-core memory-fill service interval, resident
instruction cache, prefix decode rules, one-cycle taken-forward branch refill,
measured operand latencies, x87 U-only issue/serialization, and inferred extend
instruction pairing. Unsupported is empty for all four. This walk declares no
validated shape; modeled memory/cache behavior is unvalidated. No table/overlay
was supplied. The complete returned assumptions, limiting constraints,
calibration_status and parameters_used (including every assumed/derived entry)
are copied into `build/s10-walk/twin/evidence.json`; each underlying result and
summary is retained. All three unchanged-model comparisons returned ok.

Supplemental pre-card core-small prior: the existing S9-06 card receipt exits 0
and its app log reports whole 63.410217550 s, force 0.188308615 s over 33 maps.
The options match this fallback, and both workunit files are byte-identical.
Copies are under `build/s10-walk/prior/` (receipt SHA-256
`48352891728ad5d7258a2644851915dacca2f1f0fe778f7a02ad5b24cd0dfe31`).
This prior was found before any S10 card execution. Predict combined core-small
whole about 63.4 s (engineering scenario 60–67 s), force 0.15–0.23 s. Even a free
force phase could save only 0.30% here; no material whole-run gain is expected.
The scenario range is not a calibrated confidence interval or a new measurement.
