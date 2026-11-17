# S8-09 integration Model

Numerical policy: stock N-body 1.96, crlibm, unchanged FP ordering,
`-ffp-contract=off`; bit-identical likelihood and generated body rows.
No card access. Predictions are scenarios, never measurements.
Evidence date: 2026-11-16/17. Hardware: 7120, 60 worker cores, four
contexts/core, 1.238 GHz; laptop six cores, 12 threads.

## Model before integration

| Term | Formula / counted inputs | Source | T_meas | T_pred / assumption |
| --- | --- | --- | --- | --- |
| Large serial tree | 111 builds, 20,000 bodies/build | S8-01/window 12 | card 13.19 s; laptop one core 1.11 s | S8-07 pool/CofM candidate 1-3 s, unvalidated |
| Large force | 111 walks of 20,000 bodies | S8-01/window 12 | card 13.00 s; laptop 12 threads 20.4-25.0 s | S8-08 locality candidate 8-13 s; requires card measurement |
| Large other phases | setup, integrators, likelihood | S8-01/window 12 | card approximately 1.5 s | 1.4 s with static integrators |
| Large total | tree + force + other | ticket S8-09 | card 27.4 s; best reported laptop 21.9 s | 10.4-17.4 s; only low end clears 2x |
| Core-small generation | 4,000 bodies, original quadrature node recurrence and reduction | S8-03/window 12 | card parallel quad approximately 62 s; laptop parallel quad 37 s; Stock 1.96 approximately 141 s | fast DF must reduce card below 18.5 s including evolution to clear 2x |
| Full 117676 generation | 110,000 bodies | S7-02 | laptop serial approximately 4,560 s | extrapolate only after full generated-body comparison and matching core-small measurement |
| Full 117676 evolution | 1,568 steps | S7-02 | laptop approximately 920 s | body-count scaling unknown; do not substitute the 20k Plummer ratio as a forecast |

Large tree share p = 13.19/27.42 = 0.481; eliminating it entirely has
Amdahl cap 1.93x versus the old card build. Reducing the tree alone cannot
beat the fastest reported laptop by 2x: the unchanged force plus rest is
14.4 s > 21.9/2 = 10.95 s. Both the tree and force must improve.
The generation baseline also fails the target despite beating stock x86.

T_lb: unknown for the complete application. Conditional compute bound is
interactions * 20-25 FP64 operations / 1.2e12 operations/s, pending S8-08's
actual interaction count. Do not treat a cold dependent-load path as a floor.
Memory latency, production outstanding-line capacity and fork/join cost are
unknown for this workload. Tree byte traffic and load imbalance can make a
pool slower despite removing malloc. No zero-cost allocation/barrier assumption.

T_pred: the 10.4-17.4 s large-case interval above is a falsifiable scenario,
with no claimed error calibration; reject a 2x claim unless native total
time is <= half the fastest matching laptop build. Native time must include
setup and generation; record staging overhead separately from app PHASE whole_run.
T_meas for the integrated card binary: pending lead card window.
Stock 1.96 margins require a matching case/arguments timing, not an unrelated
real-workunit time. Full-workunit extrapolation must show generation plus
1,568-step evolution separately and retain uncertainty.

Compiler items: safe compiler flag candidates use IEEE `-O3` with contraction
disabled. No app-level unsafe math or reassociation. Missed vectorization,
prefetch, scheduling and scalar x87 opportunities belong to GCC-KNC; retain a
reduced source and `-fopt-info-vec-missed` or twin refusal/evidence before filing.

Dependency status at the initial inspection: S8-05 has an unfinished fast-DF
patch; S8-07 and S8-08 do not yet have deliverable patches. No unproved fast
comparison is enabled. The installed model-first skill requests deep-tier lead
review; this ticket is the only lead channel, and the ticket authorizes
integration. This note records the review gap without inventing an approval.

## Host observations (not isolated speed measurements)

The laptop was concurrently running other ticket builds and tests. These times
are correctness-run observations; the large spread in mixed-dwarf generation
prevents using them as a clean paired speed result. The old, reported 21.9 s
large and 37 s parallel-quadrature core-small figures remain relevant competing
x86 results. Stock results below are the captured stock executable from S7-02,
SHA-256 recorded in `build/s8-09/stock-provenance.json`, not a stock-source proxy.

| Case | O3 baseline 12 thr, seconds | Integrated quick 12 thr, seconds | Integrated matrix 12 thr, seconds | Actual stock 1.96 12 thr, seconds |
| --- | ---: | ---: | ---: | ---: |
| small | 29.250000 | not run | 26.672000 | not run |
| medium | 86.609000 | not run | 65.343000 | not run |
| large | 27.656000 | 26.531000 | 30.187000 | 71.609000 |
| core-small | 42.797000 | 106.937000 | 37.219000 | 478.422000 |

Stock likelihoods match bit for bit on large and core-small. Stock core-small
printed histogram diagnostics differ at about 1e-15; the likelihood tolerance
and exact likelihood-bit gate are unchanged. The integrated large quick run:
tree 1.1564 s, force including packing/scatter 24.7707 s, whole_run 26.3527 s.
The pool performs five allocations (195,671,616 reserved bytes), rather than
cell malloc per step. These are host observations, not card forecasts.

## Full 117676 projection method

After matching card data exists, use measured full/core host generation ratio
and a separately named evolution scaling assumption:

`G_card_full = G_host_full * (G_card_core / G_host_core)`

`E_card_full = 920 s * (E_card_large / E_host_large)`

`P_card_full = G_card_full + E_card_full + remaining setup/transfer costs`.

920 s is the historical S7-02 evolution observation, not a measurement of the
integrated x86 build. Core setup is only a proxy for generation until its other
costs are removed; large is a Plummer evolution proxy for mixed-dwarf 117676.
Propagate these mismatches as uncertainty. No full-workunit 2x forecast can be
asserted from the current evidence. In particular, 62/37 > 1 for the old
core-small card/optimized-host generation ratio already rejects a credible 2x
projection for the unchanged generator. Do not compare card time only with the
old 5,488 s host total after accelerating host generation too.

## Compiler items

1. `probes/s8_subindex.c`, compiled from O2/O3 binaries with actual instruction
   lengths: four contexts both take 1,533 predicted cold core cycles total,
   383.25/classification. `functional` passes all four independent outputs.
   Twin `compare` returns a tie. This cold helper experiment is an
   `unvalidated_scenario_estimate`, with miss_stall 2,095 and x87_serial 1,087
   context-cycles among the constraints; it does not rank complete trees.
   Exact assumptions, unsupported (empty), calibration status and all eleven
   assumed/derived parameters are retained in
   `build/s8-09/twin-report-fields.json` and the original result files.
2. `probes/s8_df_reuse.c` and `scripts/s8_compiler_items.sh`: the normal finite
   DF stencil has 20 potential + 9 density calls. Giving the model samplers a
   valid read-only promise lets existing GCC eliminate repeated samples to
   10 + 5 calls, without changing the FP expression order. This is a compiler
   opportunity, not a demonstrated backend bug or a measured speedup. The real
   dispatchers contain lazy initialization, so globally promising purity would
   be invalid; a proven ready-model API or interprocedural specialization is
   required. `-fopt-info-vec-missed` diagnostics and both emitted assemblies are
   in `build/s8-09/compiler-item/`. Full tree missed-vectorization diagnostics
   are retained there too. No unsafe arithmetic or global pure annotation was
   introduced in the application.

## Native measurements

Pending: no `## Card results` has been appended to S8-09 at this update.
Batch 1 is the frozen O3/quad baseline; batch 2 is pool + scalar walk layout.
No predicted number is promoted to T_meas. Reconcile this section and the
phase table from successful matching receipts after the lead's runs.

## Completed dependency evidence

S8-07 final commit 8a44481 (lead note 01:00Z): 69,420 every-step identity checks
pass. The integration imported its final root-in-arena fix after batch 2;
batch 3 supersedes batch 2. A new production matrix is running for that final
source. Source hashes are `build/s8-09/integration-inputs-final.json`.

S8-08 completed: imported counting/model/twin evidence is retained separately
as `s8-force-{model.md,counts.csv,twin.json}`. Counts for the original
20k Plummer tree are 697,048,696 cell and 195,818,758 body interactions,
1,087,300,798 visits and 44,114,931,372 source FP64 operations. Ideal compute
T_lb = 0.036762 s; conditional x87 throughput floor with overlap = 1.632073 s.
All-cold latency scenario = 2.910158 s, not a lower bound. Compared with the
13.0 s measured force phase, even the largest simple scenario leaves substantial
unmodeled cost. The packed pool/view changes addresses and reuse; these counts
and scenarios do not calibrate a prediction for the combined candidate.

S8-08's four scalar/vector variants on four-context core and 8-tile ring return
unsupported (uncosted cold nbReportTreeIncest call) or budget_exhausted (vector,
30-second interpreter budget). Every prediction is null; none is a functional
pass or ranking. The integration's final-binary adapter attempts also identify
missing nbBuildTree/OpenMP/external-potential callee closures. Do not invent
callee costs or remove cold blocks to obtain an apparent winning number.

S8-05's retained full fast-DF generated rows match the checkpoint reference:
6,160,000 bytes, SHA-256 d09e23bcd50852add7f7bea4f8c9e68f6d18e4d39b2a302503d4bceaad23209f.
Observed fast-DF generation: core-small 49.0197533 s, 133/4,000 fallbacks; full
1,973.0770402 s, 3,766/110,000 fallbacks. These are sibling evidence, not our
proof. Its node callback is still scalar and eight-node blocks expose only
about 42 workers for 330 nodes. The current exact parallel quadrature exposes
all 330 independent nodes, avoids guarded/replay overhead, and has faster
reported host generation (~37 s). Fast DF is therefore not selected merely
because its name suggests vector speed; our independent full exact capture now matches all 6,160,000 reference bytes. Correctly rounded node math/vectorization remains the
compiler/guarded-math opportunity.

Native host competition: unrestricted -march=native exited 2816 before a
likelihood (retained binary/build logs under build/s8-09/native-failure/).
The cause is not established; no debugger is supplied and none was installed.
Portable vector-force large/core-small likelihoods are bit-identical, with
observed times 32.078/49.641 s. Native-tuned SSE scalar/vector competitors both pass exact large/core-small likelihood checks; the vector competitor records 23.453/35.219 s.
Failed candidates are excluded from timing minima. The legacy 21.9/37 s host
observations cap the comparison denominator to avoid booking a gain against
contended slow host measurements. A global optimum over all x86 flags and
runtime placements is not proven.

## Final host proof, 02:04Z

All twelve final production comparisons and all twelve tree-check comparisons
pass: small, medium, large, core-small at 1/4/12 threads. All likelihood bits,
printed and saved histogram scientific tokens match. The tree companion checks
52,164 builds against a serial tree, including topology, body order, cell values,
radii, quadrupoles and links on every step.

Independent exact generation: core-small 224,000 bytes (SHA-256
7117b750caad318ab42a781346ca480a9f43fa1828e0832b58ad06fc00b88b59), full 117676
6,160,000 bytes (SHA-256
d09e23bcd50852add7f7bea4f8c9e68f6d18e4d39b2a302503d4bceaad23209f).
Captured generation times: 38.1417771 s and 1,088.7515507 s; all workers have
x87 CW 027f with zero mismatches. These are host observations.

The existing 50-75 s core generation scenario extrapolates by the measured
full/core generation ratio 28.5449 to about 1.43-2.14 ks of card generation alone.
The host reference proxy is 1,088.75 + 920 = 2,008.75 s, with historical evolution
and compiler/load mismatch; it is not the best integrated full-task measurement.
This scenario does not keep 2x even before card evolution is added. A new
vectorized node kernel with a nonzero rigorous node-error certificate remains
required if the native measurements confirm the generation bottleneck. Replacing
crlibm with a within-1-ULP library is insufficient without propagating that error
through the finite-difference cancellation and guarded comparisons.

The fastest exact core-small competitor observed is 35.219 s, so the necessary
card total ceiling is 17.6095 s. Large's conservative competing observation is
21.9 s, giving a 10.95 s ceiling. Card time, margin over stock, and a calibrated
full-task projection remain unmeasured until successful native receipts exist.

## Final sequential host comparison

All five binaries ran sequentially after the heavy validation jobs; ambient
laptop activity was not controlled. All ten likelihoods are bit-identical.
Stock core-small histogram diagnostics retain their approximately 1e-15
difference; no likelihood tolerance or bit check changed.

| Build (12 threads) | Large seconds | Core-small seconds |
| --- | ---: | ---: |
| portable-scalar | 18.000 | 33.219 |
| native-sse-scalar | 17.969 | 34.921 |
| native-sse-vector | 22.141 | 34.547 |
| portable-vector | 22.984 | 35.156 |
| stock-196 | 23.078 | 149.344 |

The exact tree-identity companion also recorded 19.000/31.391 s. Counting
all valid competitors conservatively, the observed minima are 17.969 s large
and 31.391 s core-small: required card ceilings 8.9845 and 15.6955 s. The
selected scalar-card scenario (10.4-17.4 s / 50-75 s) does not predict those
2x wins. Native timing is still required. Stock margin must use the sequential
23.078/149.344 s captures, rather than the earlier contended 71.609/478.422 s.

Patch classes were split on the lead's M5 instruction: optimizations, timers,
and proof/counter hooks are separate patch files, with defaults documented in
patches/README.md. Both full replay and correctness-only replay pass; the full
sequence reconstructs the already-tested application source unchanged. The
correctness-only fixture contains none of the new optimization/timer hooks.
