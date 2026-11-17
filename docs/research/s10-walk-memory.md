# S10-07 walk memory experiment

Model table recorded before changing the force path (2026-11-17).
Inputs: S10-02's actual initial 20,000-body large-tree snapshot, unchanged
64/96/160-byte node/body/cell ABI. `scripts/model-s10-memory.py` executes an
independent binary64 tree walk and counts distinct 64-byte lines for exactly
the source fields read. It compares the same 1,053 evenly sampled generation
indices in generation order (called random here) and threaded-tree DFS order.
Each complete core chunk has 16 targets, four consecutive targets per sibling.
The sample is sparser than consecutive full-tree bodies: locality is conditional.

## Model table

| Term | Formula / counted inputs | Random | Spatial | Scope and assumptions |
| --- | --- | ---: | ---: | --- |
| Tree visits/body | exact opening predicates on captured positions | 487.54 | 487.54 | Initial large tree; arithmetic unchanged |
| Distinct lines/body | union of all node field reads | 1,073.70 | 1,073.70 | Excludes stack, code, output, caller |
| Lines/thread chunk | union over four bodies | 1,995.46 | 1,462.22 | 263 complete chunks; cold union, not cache misses |
| Lines/core chunk | union over 16 bodies | 4,047.97 | 2,424.74 | 65 complete chunks, 39.9% fewer distinct lines |
| Bytes/core chunk | preceding row times 64 | 259,070 | 155,183 | Could fit physical 512 KiB L2, not necessarily L1 |
| 4 KiB pages/core chunk | union of line addresses / 4096 | 559.35 | 387.43 | Both exceed 64-entry small-page DTLB |
| 2 MiB virtual regions/core chunk | union of line addresses / 2097152 | 4 | 4 | Host fragmentation; NOT proof of card huge-page allocation |
| Translation charge | 29 cycles per modeled small-page miss | unknown | unknown | Page union does not count replacement misses |
| Existing walk observation | ticket's Window 8 per-thread walk | ~3.05 s | unmeasured | Large; reported, not rerun here |
| Existing one-core twin | ticket's baseline | 148,351 cycles/body | pending | Unvalidated tree shape |
| Added work | DFS visits + nbody index stores + indirect index/body | none | O(nodes + bodies)/map | Serial permutation; 80 KB indices at 20k |
| Force phase Amdahl cap | walk share, about 25% on large | <=25% force reduction | <=25% force reduction | Ticket S10-06 says ~75% external potential; whole-program share unknown |

`T_lb`: unknown; unions are not measured traffic and no qualified loaded-latency
or issue bound exists for this full force map. `T_pred`: locality should reduce
miss pressure on a shared core, with a risk of static scheduling imbalance.
Hypothesis before twin/card: order 0-20% lower walk time; huge 0-10%; combined
0-25%. These are screening bands, not calibrated forecasts. No winner is
selected within the optimize workflow's 20% conservative uncertainty rule.
For the large force phase, this implies roughly 0-5%, 0-2.5%, 0-6.25% respectively
before permutation/allocation overhead; real-steps needs native measurement.

MPSS evidence is local read-only documentation:
`gcc_knc/docs/research/knc-memory-bandwidth.md`, OS/pages and S11-06: MPSS 3.7,
THP enabled but AnonHugePages observed zero; explicit huge pages succeeded,
`/mnt/huge` and overcommit available. The later lead note in S10-07 checks the current card: THP is `[always]`,
2 MiB; the reserved pool is empty. Accordingly native allocation uses 2 MiB
alignment and rounded sizes with MADV_HUGEPAGE, retaining valid small-page
backing when promotion does not happen. No kernel settings are changed.
Card page diagnostics must inspect the mapping at its live address. Cygwin
cannot establish MPSS page availability. The twin's 2 MiB switch would affect
all simulated pages including the stack; we do not claim that as a faithful
mixed-backing huge-page forecast.

The installed model-first skill is absent. This table follows knc-optimize's
minimal accounting fallback. Compiler-owned scheduling/vectorization/x87 work
is unchanged; this experiment changes legal target order and native backing.

## Compiled twin predictions (recorded before card execution)

Whole linked `nbGravity`, GCC-KNC -O2, release options plus phase timers (off
inside the function). The target stream uses the new build's complete initial
large-tree capture. Host and card ABI offset tables must match. Each output is
checked against the independent binary64 oracle; no call stubs or instruction
substitutions are used. Calls tables omit caller/permutation/dispatch costs.
Cold memory, all branches predicted, the same card-7120-measured profile and
53-bit x87 policy on both orders. Raw kernels, input provenance and tool output
are under `build/s10-memory/twin/`.

The core diagnostic uses two calls per context, four contexts/core. This is
narrower than the application's four-body static chunks. Core uses the same
8 generation indices distributed over the full body range, then DFS sorts
that same set; ring uses the same 32 targets with disjoint four-target chunks on eight
tiles, one complete call per context. The sample therefore cannot represent all neighbouring bodies
or later-step cache state. Changing order also changes work balance among
contexts. Do not extrapolate these finite cold streams to card throughput.

| Core order | Completion cycles / 8 calls | Dynamic instructions | L2 hits | Memory accesses | DTLB misses | Status |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Generation/random | 119,423.125 | 351,511 | 3,909 | 1,443 | 1,139 | ok; oracle checks all xyz outputs |
| Spatial | 127,993.625 | 351,511 | 4,384 | 1,481 | 1,249 | ok; oracle checks all xyz outputs |

The spatial sample is slower, within the conservative 20% decision band: no
clear winner. This is an `unvalidated_scenario_estimate`, not a calibrated
forecast or card measurement. The sparse finite matched sample provides no
confirmed gain despite the larger host counter table's locality opportunity.
The initial positive screening ranges remain hypotheses to test, with this
negative sample now explicitly included in the card predictions.

Each result's complete `assumptions`, `unsupported`, `limiting_constraints`,
`calibration_status` and `parameters_used` are retained without abbreviation in
`twin/evidence.json` and the corresponding `result.json`. In particular: LRU
approximates hardware replacement; small-page DTLB is 64-entry fully associative
with 29-cycle miss charge and no second-level walk model; L2 hardware prefetch
and memory service are modeled; no held-out tree-walk shape is declared.
Core limiting terms include resource issue, dependencies, miss stalls and x87
serialization. None of these observations authorizes a compiler performance
patch in this repository.

## Build, proof and operator handoff

Run `bash scripts/test-s10-memory.sh` from this worktree. It creates and exports
TMPDIR, TMP and TEMP under `build/tmp` before compiling. All compiles use the
pinned Cygwin and GCC-KNC tools, with two make jobs. No downloads, installs or
Git writes are needed. The model input is the retained S10-02 capture; no card
access is required to rerun this workflow.

`build/s10-memory/card-release-{base,order,huge,both}/` holds exact release.env
binaries plus the indicated memory options, with PHASE_TIMERS=0. The separate
`card-{base,order,huge,both}/` copies have PHASE_TIMERS=1 for the timing window.
`card-pages/` enables only the separate mapping diagnostic in addition to the
combined options and timers. Proof/counter hooks are off in timing binaries.
The card launcher uses a compiled helper to inspect the runner-authorized CPU
mask and sysfs topology, and refuses unless it contains 60 groups of four
siblings. It then supplies sibling-grouped GOMP_CPU_AFFINITY to every variant,
including the baseline. No Python installation on MPSS is required.

The lead's authorized window is `bash build/s10-memory/window.sh`: four
variants times large and real-steps if present (core-small otherwise), plus
one large page diagnostic. It uses this checkout's tools/card_run and collects
application stderr. No card job is executed by the engineer. The page diagnostic
reads live body and tree addresses from /proc/self/smaps immediately before the
initial walk inside the force phase; AnonHugePages is actual backing evidence,
while alignment and successful advice alone are not. KernelPageSize and
MMUPageSize can remain 4 KiB even when AnonHugePages is nonzero. Check each named
mapping and retain fallback/no-promotion results rather than treating a requested
option as a huge-page success. Timing/ranking must exclude the diagnostic job.

The initial two-call ring attempt stopped with `budget_exhausted` and
`fabric event budget exhausted` after 624.2946 reported Python host seconds.
Its partial diagnostics are not predictions. The companion in-flight trial
was interrupted after this resource limit was identified. Both original inputs
and available output are retained in `twin/initial-two-call-attempt/`. The
final ring diagnostic uses one call/context with an 8,000,000-event budget and
1,800-second per-command limit, preserving the 8-tile geometry and full four contexts/tile. That attempt also
hit the fabric event budget after 572.7897 Python host seconds; it and the
interrupted companion are retained in `twin/full-background-one-call/`. The
final completed-check scenario explicitly disables synthetic background: only
the eight detailed cores are active. It is an eight-core overlook, not a
full-card forecast. Core results are reused only
when the complete generated input file is byte-identical.

S10-06 made real-steps available during this ticket. The frozen Lua, histogram
and README in `workunits/real-steps` are copied byte-for-byte from S10-06 and
verified against the main checkout; hashes are in `real-steps-source.json`.
The final required proof and window use that case rather than core-small.

`AnonHugePages` is a VMA aggregate: if allocations share a VMA, it does not
prove that every byte of either allocation has huge backing. Retain the
printed address ranges and page diagnostics with each native result.

The existing tree allocation subcounters do not charge the direct huge-eligible
pool allocation; the enclosing tree/setup wall timers still include it. Do not
interpret those subcounters as complete allocation totals for the huge variants.

S10-06 published inputs but its idle gate blocked all new reference runs.
Accordingly real-steps is checked against this ticket's off-option release
baseline at every force evaluation; there is no claimed independent stock
real-steps reference or host performance ranking. Small, medium and large
also match the archived independent science and force references.

## Completed host force proof

| Case | Bodies | Force evaluations/run | Result |
| --- | ---: | ---: | --- |
| small | 64 | 8622 | 4/4; xyz bytes and science exact |
| medium | 1024 | 8622 | 4/4; xyz bytes and science exact |
| large | 20000 | 111 | 4/4; xyz bytes and science exact |
| real-steps | 20000 | 129 | 4/4; xyz bytes and science exact |

Every evaluation, including the initial setup evaluation, is compared as the
full original-index xyz byte stream. `compare.py` also passes, and parsed
likelihood/histogram values compare exactly. The reference and all three
options have identical full-stream SHA-256 values for each case; hashes and
commands are in `build/s10-memory/proof.json` and isolated run directories.
Small uses one host thread, medium baseline one and candidates four, large
and real-steps four. Earlier four-variant core-small proofs also passed
(33 evaluations at 4,000 bodies), before S10-06 supplied the required real case.
These contended host runs establish correctness, not a speed ranking.

## Completed eight-tile overlook

Both final ring streams returned `ok`, each with 32/32 whole-call xyz
oracle checks. The order comparison gives no clear difference within a wide unvalidated band.
The leading first-cause stalls are resource, core_local_miss, dependency in
generation order and resource, core_local_miss, dependency in spatial order.
This describes the eight fully simulated cores without extra synthetic cores;
there is no calibrated multicore error bar, full-card throughput claim, cycle
forecast or speedup claim. Raw numerical tool output is retained for audit
only. Both core runs also returned `ok` (8/8 oracle checks each).
